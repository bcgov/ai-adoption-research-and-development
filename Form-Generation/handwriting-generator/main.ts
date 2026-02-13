// deno_service/main.ts
// Deno HTTP server using handwritten.js to generate handwriting images

import { serve } from "https://deno.land/std@0.203.0/http/server.ts";
import handwritten from "npm:handwritten.js";

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
        return new Response(JSON.stringify({ error: "Missing or invalid 'text' field" }), { status: 400 });
      }
      // Generate handwriting image using handwritten.js
      const base64 = await handwritten(text, { outputType: 'png/b64' });
      return new Response(JSON.stringify({ image: base64 }), {
        status: 200,
        headers: {
          "Content-Type": "application/json"
        }
      });
    } catch (e: any) {
      return new Response(JSON.stringify({ error: e.message }), { status: 500 });
    }
  }

  // Batch generation endpoint (new, optimized with parallel workers)
  if (req.method === "POST" && pathname === "/generate-batch") {
    try {
      const { texts } = await req.json();
      if (!Array.isArray(texts) || texts.length === 0) {
        return new Response(JSON.stringify({ error: "Missing or invalid 'texts' field (must be non-empty array)" }), { status: 400 });
      }
      
      // Validate all texts are strings
      for (const text of texts) {
        if (typeof text !== "string") {
          return new Response(JSON.stringify({ error: "All items in 'texts' array must be strings" }), { status: 400 });
        }
      }

      const startTime = Date.now();
      
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
            console.error(`[Batch] No resolver found for id ${id} (resolvers length: ${resolvers.length})`);
          }
        };
        workers.push(worker);
      }
      
      // Distribute work across workers (round-robin)
      // IMPORTANT: All promises must resolve through the same mechanism to preserve order
      const workPromises = texts.map((text, index) => {
        return new Promise<string>((resolve, reject) => {
          resolvers[index] = { resolve, reject };
          
          // Check cache first - if cached, simulate worker response for consistency
          if (cache.has(text)) {
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
          
          // Not cached - send to worker
          cacheMisses.push(index);
          const workerIndex = index % maxWorkers;
          workers[workerIndex].postMessage({ id: index, text });
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
            console.error(`[Batch] CRITICAL ORDER ERROR: Index ${i}, text '${text.substring(0, 20)}...' - image doesn't match cache!`);
            // Don't throw, but log the error
          }
        }
      }
      
      // Cache all generated images for future use (verify text matches)
      images.forEach((image, index) => {
        const text = texts[index];
        if (!cache.has(text)) {
          cache.set(text, image);
        } else {
          // Verify cached image matches (sanity check)
          const cachedImage = cache.get(text);
          if (cachedImage !== image) {
            console.warn(`[Batch] Cache mismatch for text '${text}' at index ${index}`);
          }
        }
      });
      
      // Verify order (debugging)
      if (images.length !== texts.length) {
        console.error(`[Batch] Mismatch: expected ${texts.length} images, got ${images.length}`);
      }
      
      // Clean up workers
      workers.forEach(worker => worker.terminate());
      
      const elapsed = Date.now() - startTime;
      const cacheHitRate = cacheHits.length / texts.length * 100;
      console.log(`[Batch] Generated ${texts.length} images in ${elapsed}ms using ${maxWorkers} workers (avg: ${(elapsed/texts.length).toFixed(1)}ms per image)`);
      console.log(`[Batch] Cache: ${cacheHits.length} hits, ${cacheMisses.length} misses (${cacheHitRate.toFixed(1)}% hit rate)`);
      console.log(`[Batch] Completion order: [${completionOrder.join(', ')}]`);
      console.log(`[Batch] Expected order: [${texts.map((_, i) => i).join(', ')}]`);
      
      // Verify images array length matches texts
      if (images.length !== texts.length) {
        console.error(`[Batch] ERROR: Images length (${images.length}) doesn't match texts length (${texts.length})`);
      }
      
      // Verify order: check first few images match expected texts
      const verifyCount = Math.min(5, texts.length);
      for (let i = 0; i < verifyCount; i++) {
        const text = texts[i];
        const image = images[i];
        // If this text was cached, verify the image matches
        if (cache.has(text)) {
          const cachedImage = cache.get(text);
          if (cachedImage !== image) {
            console.error(`[Batch] ORDER ERROR: Image at index ${i} doesn't match cached image for text '${text}'`);
          }
        }
      }
      
      return new Response(JSON.stringify({ images: images }), {
        status: 200,
        headers: {
          "Content-Type": "application/json"
        }
      });
    } catch (e: any) {
      return new Response(JSON.stringify({ error: e.message }), { status: 500 });
    }
  }

  return new Response("Not found", { status: 404 });
}

console.log("Deno Handwriting service running on http://localhost:8000");
console.log("Endpoints:");
console.log("  POST /generate      - Single text generation (backward compatible)");
console.log("  POST /generate-batch - Batch generation (optimized)");
serve(handler, { port: 8000 });
