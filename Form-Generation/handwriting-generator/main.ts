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

  // Batch generation endpoint (new, optimized)
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

      // Generate all images in parallel using Promise.all
      const startTime = Date.now();
      const imagePromises = texts.map(text => 
        handwritten(text, { outputType: 'png/b64' })
      );
      const images = await Promise.all(imagePromises);
      const elapsed = Date.now() - startTime;
      
      console.log(`[Batch] Generated ${texts.length} images in ${elapsed}ms (avg: ${(elapsed/texts.length).toFixed(1)}ms per image)`);
      
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
