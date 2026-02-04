// deno_service/main.ts
// Deno HTTP server using handwritten.js to generate handwriting images

import { serve } from "https://deno.land/std@0.203.0/http/server.ts";
import handwritten from "npm:handwritten.js";

async function handler(req: Request): Promise<Response> {
  if (req.method === "POST" && new URL(req.url).pathname === "/generate") {
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
  return new Response("Not found", { status: 404 });
}

console.log("Deno Handwriting service running on http://localhost:8000");
serve(handler, { port: 8000 });
