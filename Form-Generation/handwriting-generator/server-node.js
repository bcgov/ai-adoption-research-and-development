#!/usr/bin/env node
/**
 * Node server that uses the local patched handwritten.js (with lineWidth support).
 * API: POST /generate, POST /generate-batch.
 * Run: node server-node.js   (from handwriting-generator dir, or set HANDWRITTEN_PATH)
 */

const http = require("http");
const path = require("path");

const HANDWRITTEN_PATH = process.env.HANDWRITTEN_PATH || path.join(__dirname, "..", "handwritten.js");
const handwritten = require(HANDWRITTEN_PATH);

const PORT = 8000;

function log(level, msg, ...args) {
  const ts = new Date().toISOString();
  console.log(`[${ts}] [${level}] ${msg}`, ...args);
}

async function handleGenerate(body) {
  const { text, options = {} } = body;
  if (!text || typeof text !== "string") {
    return { status: 400, body: { error: "Missing or invalid 'text' field" } };
  }
  const start = Date.now();
  try {
    const base64 = await handwritten(text, { outputType: "png/b64", ...options });
    const result = Array.isArray(base64) ? base64[0] : base64;
    log("INFO", `Single /generate: done in ${Date.now() - start} ms`);
    return { status: 200, body: { image: result } };
  } catch (e) {
    log("ERROR", "Single /generate failed:", e.message);
    return { status: 500, body: { error: e.message } };
  }
}

async function handleBatch(body) {
  const { texts, options: batchOptions } = body;
  if (!Array.isArray(texts) || texts.length === 0) {
    return { status: 400, body: { error: "Missing or invalid 'texts' (must be non-empty array)" } };
  }
  const options = batchOptions && typeof batchOptions === "object" ? batchOptions : undefined;
  const startTime = Date.now();
  log("INFO", `Batch: start count=${texts.length}`);
  const images = [];
  for (let i = 0; i < texts.length; i++) {
    const text = texts[i];
    if (typeof text !== "string") {
      return { status: 400, body: { error: "All items in 'texts' must be strings" } };
    }
    try {
      const base64 = await handwritten(text, { outputType: "png/b64", ...options });
      images.push(Array.isArray(base64) ? base64[0] : base64);
    } catch (e) {
      log("ERROR", `Batch item ${i} failed:`, e.message);
      return { status: 500, body: { error: e.message } };
    }
  }
  const elapsed = Date.now() - startTime;
  log("INFO", `Batch: done count=${texts.length} elapsed=${elapsed} ms`);
  return { status: 200, body: { images } };
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url || "", `http://localhost`);
  if (req.method !== "POST") {
    res.writeHead(404);
    res.end("Not found");
    return;
  }

  let body = "";
  for await (const chunk of req) body += chunk;
  let json;
  try {
    json = JSON.parse(body);
  } catch {
    res.writeHead(400);
    res.end(JSON.stringify({ error: "Invalid JSON" }));
    return;
  }

  let result;
  if (url.pathname === "/generate") {
    result = await handleGenerate(json);
  } else if (url.pathname === "/generate-batch") {
    result = await handleBatch(json);
  } else {
    res.writeHead(404);
    res.end("Not found");
    return;
  }

  res.writeHead(result.status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(result.body));
});

server.listen(PORT, () => {
  log("INFO", `Handwriting service (Node, local patched) listening on http://localhost:${PORT}`);
  log("INFO", "Endpoints: POST /generate (single), POST /generate-batch (batch)");
});
