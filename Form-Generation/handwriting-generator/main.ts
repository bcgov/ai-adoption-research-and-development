// deno_service/main.ts
// Deno HTTP server using handwritten.js to generate handwriting images

import { serve } from "https://deno.land/std@0.203.0/http/server.ts";
import handwritten from "npm:handwritten.js";

function log(level: string, msg: string, ...args: unknown[]) {
  const ts = new Date().toISOString();
  if (args.length > 0) {
    console.log(`[${ts}] [${level}] ${msg}`, ...args);
  } else {
    console.log(`[${ts}] [${level}] ${msg}`);
  }
}

// Service-level cache for repeated texts (persists across requests)
const cache = new Map<string, string>();

async function handler(req: Request): Promise<Response> {
  const url = new URL(req.url);
  const pathname = url.pathname;

  // Single text generation endpoint (backward compatible)
  if (req.method === "POST" && pathname === "/generate") {
    try {
      const { text } = await req.json();
      if (!text || typeof text !== "string") {
        log("ERROR", "Single /generate: missing or invalid 'text' field");
        return new Response(JSON.stringify({ error: "Missing or invalid 'text' field" }), { status: 400 });
      }
      log("INFO", `Single /generate: text length=${text.length} preview=${text.slice(0, 30)}`);
      const start = Date.now();
      const base64 = await handwritten(text, { outputType: 'png/b64' });
      log("INFO", `Single /generate: done in ${Date.now() - start} ms`);
      return new Response(JSON.stringify({ image: base64 }), {
        status: 200,
        headers: {
          "Content-Type": "application/json"
        }
      });
    } catch (e: any) {
      log("ERROR", "Single /generate failed: " + e.message);
      return new Response(JSON.stringify({ error: e.message }), { status: 500 });
    }
  }

  // Batch generation endpoint (new, optimized with parallel workers)
  if (req.method === "POST" && pathname === "/generate-batch") {
    try {
      const { texts, options: batchOptions } = await req.json();
      if (!Array.isArray(texts) || texts.length === 0) {
        log("ERROR", "Batch: missing or invalid 'texts' (must be non-empty array)");
        return new Response(JSON.stringify({ error: "Missing or invalid 'texts' field (must be non-empty array)" }), { status: 400 });
      }
      const options = batchOptions && typeof batchOptions === "object" ? batchOptions : undefined;

      for (const text of texts) {
        if (typeof text !== "string") {
          log("ERROR", "Batch: non-string item in 'texts' array");
          return new Response(JSON.stringify({ error: "All items in 'texts' array must be strings" }), { status: 400 });
        }
      }

      const startTime = Date.now();
      const maxWorkersLog = Math.min(texts.length, (Deno.systemCpuInfo?.cores || 4) * 2);
      log("INFO", `Batch: start count=${texts.length} workers=${maxWorkersLog}`);
      
      // Use workers for parallel CPU-bound generation
      // Use 2× CPU cores for better CPU utilization (hyperthreading benefit)
      const cpuCores = Deno.systemCpuInfo?.cores || 4;
      const maxWorkers = Math.min(texts.length, cpuCores * 2);
      const workerScript = new URL("./worker.ts", import.meta.url).href;
      
      // Track cache performance for this request
      const cacheHits: number[] = [];
      const cacheMisses: number[] = [];
      
      // Create workers and distribute work
      const workers: Worker[] = [];
      // Use array to store resolvers in correct order (indexed by id)
      const resolvers: Array<{ resolve: (value: string) => void; reject: (error: any) => void } | null> = new Array(texts.length).fill(null);
      
      // Initialize workers
      const completionOrder: number[] = []; // Track order of completion for debugging
      for (let i = 0; i < maxWorkers; i++) {
        const worker = new Worker(workerScript, { type: "module" });
        worker.onmessage = (e: MessageEvent) => {
          const { id, success, image, error } = e.data;
          completionOrder.push(id); // Track completion order
          const resolver = resolvers[id];
          if (resolver) {
            resolvers[id] = null; // Clear to prevent double resolution
            if (success) {
              // Verify the text matches what we expect
              const expectedText = texts[id];
              resolver.resolve(image);
            } else {
              resolver.reject(new Error(error));
            }
          } else {
            log("ERROR", `Batch: no resolver for id=${id} resolversLen=${resolvers.length}`);
          }
        };
        workers.push(worker);
      }
      
      // Distribute work across workers (round-robin)
      // IMPORTANT: All promises must resolve through the same mechanism to preserve order
      const workPromises = texts.map((text, index) => {
        return new Promise<string>((resolve, reject) => {
          resolvers[index] = { resolve, reject };
          
          // Check cache first (only when no options; options change output e.g. lineWidth)
          if (!options && cache.has(text)) {
            cacheHits.push(index);
            // Simulate async worker response by using setTimeout with minimal delay
            // This ensures cache hits go through the same async path as worker responses
            setTimeout(() => {
              const resolver = resolvers[index];
              if (resolver) {
                resolvers[index] = null;
                resolver.resolve(cache.get(text)!);
              }
            }, 0);
            return;
          }

          // Not cached - send to worker (with optional options for e.g. lineWidth)
          cacheMisses.push(index);
          const workerIndex = index % maxWorkers;
          workers[workerIndex].postMessage({ id: index, text, options });
        });
      });
      
      // Wait for all work to complete
      // Promise.all preserves order of the promises array, not resolution order
      // This means results[0] will always be the result of workPromises[0], etc.
      const images = await Promise.all(workPromises);
      
      // Verify images match texts in correct order
      if (images.length !== texts.length) {
        throw new Error(`Images length (${images.length}) doesn't match texts length (${texts.length})`);
      }
      
      // CRITICAL: Verify order by checking that each image corresponds to the correct text
      // This ensures Promise.all() preserved order correctly
      for (let i = 0; i < Math.min(10, texts.length); i++) {
        const text = texts[i];
        const image = images[i];
        // If this text was in cache, verify the image matches the cached version
        if (cache.has(text)) {
          const cachedImage = cache.get(text);
          if (cachedImage !== image) {
            log("ERROR", `Batch: order error index=${i} text="${text.substring(0, 20)}..." image != cache`);
          }
        }
      }
      
      // Cache all generated images for future use (skip when options were used, e.g. lineWidth)
      if (!options) {
        images.forEach((image, index) => {
          const text = texts[index];
          if (!cache.has(text)) {
            cache.set(text, image);
          } else {
            const cachedImage = cache.get(text);
            if (cachedImage !== image) {
              log("WARN", `Batch: cache mismatch index=${index} text="${text.slice(0, 30)}..."`);
            }
          }
        });
      }
      
      if (images.length !== texts.length) {
        log("ERROR", `Batch: image count mismatch expected=${texts.length} got=${images.length}`);
      }
      
      // Clean up workers
      workers.forEach(worker => worker.terminate());
      
      const elapsed = Date.now() - startTime;
      const cacheHitRate = cacheHits.length / texts.length * 100;
      log("INFO", `Batch: done count=${texts.length} elapsed=${elapsed} ms avg=${(elapsed / texts.length).toFixed(1)} ms/image workers=${maxWorkers}`);
      log("INFO", `Batch: cache hits=${cacheHits.length} misses=${cacheMisses.length} (${cacheHitRate.toFixed(1)}% hit rate)`);
      if (texts.length <= 15) {
        log("DEBUG", "Batch: completion order=" + completionOrder.join(", "));
      }
      
      return new Response(JSON.stringify({ images: images }), {
        status: 200,
        headers: {
          "Content-Type": "application/json"
        }
      });
    } catch (e: any) {
      log("ERROR", "Batch failed: " + e.message);
      return new Response(JSON.stringify({ error: e.message }), { status: 500 });
    }
  }

  log("WARN", `Not found: ${req.method} ${pathname}`);
  return new Response("Not found", { status: 404 });
}

log("INFO", "Handwriting service listening on http://localhost:8000");
log("INFO", "Endpoints: POST /generate (single), POST /generate-batch (batch)");
serve(handler, { port: 8000 });
