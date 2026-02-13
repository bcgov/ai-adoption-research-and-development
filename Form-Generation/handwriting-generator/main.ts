// deno_service/main.ts
// Deno HTTP server using handwritten.js to generate handwriting images

import { serve } from "https://deno.land/std@0.203.0/http/server.ts";
import handwritten from "npm:handwritten.js";

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
      // Limit concurrent workers to avoid overwhelming the system
      // Deno doesn't have navigator.hardwareConcurrency, use reasonable default
      const cpuCores = Deno.systemCpuInfo?.cores || 4;
      const maxWorkers = Math.min(texts.length, cpuCores);
      const workerScript = new URL("./worker.ts", import.meta.url).href;
      
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
              resolver.resolve(image);
            } else {
              resolver.reject(new Error(error));
            }
          } else {
            console.error(`[Batch] No resolver found for id ${id}`);
          }
        };
        workers.push(worker);
      }
      
      // Distribute work across workers (round-robin)
      // Create promises in order and ensure they resolve in order
      const workPromises = texts.map((text, index) => {
        return new Promise<string>((resolve, reject) => {
          resolvers[index] = { resolve, reject };
          const workerIndex = index % maxWorkers;
          // Send message with explicit index to ensure correct mapping
          workers[workerIndex].postMessage({ id: index, text, index });
        });
      });
      
      // Wait for all work to complete
      // Promise.all preserves order of the promises array, not resolution order
      // This means results[0] will always be the result of workPromises[0], etc.
      const images = await Promise.all(workPromises);
      
      // Verify order (debugging)
      if (images.length !== texts.length) {
        console.error(`[Batch] Mismatch: expected ${texts.length} images, got ${images.length}`);
      }
      
      // Clean up workers
      workers.forEach(worker => worker.terminate());
      
      const elapsed = Date.now() - startTime;
      console.log(`[Batch] Generated ${texts.length} images in ${elapsed}ms using ${maxWorkers} workers (avg: ${(elapsed/texts.length).toFixed(1)}ms per image)`);
      console.log(`[Batch] Completion order: [${completionOrder.join(', ')}]`);
      console.log(`[Batch] Expected order: [${texts.map((_, i) => i).join(', ')}]`);
      
      // Verify images array length matches texts
      if (images.length !== texts.length) {
        console.error(`[Batch] ERROR: Images length (${images.length}) doesn't match texts length (${texts.length})`);
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
