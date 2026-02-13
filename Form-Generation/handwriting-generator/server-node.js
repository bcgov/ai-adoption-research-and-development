#!/usr/bin/env node
/**
 * Node server that uses the local patched handwritten.js (with lineWidth support).
 * Optimized: parallel worker pool (2× CPU cores) + in-memory cache for repeated texts.
 * API: POST /generate, POST /generate-batch.
 */

const http = require("http");
const path = require("path");
const os = require("os");
const { Worker } = require("worker_threads");

const HANDWRITTEN_PATH = process.env.HANDWRITTEN_PATH || path.join(__dirname, "..", "handwritten.js");
const PORT = 8000;
// Worker pool size: HANDWRITING_WORKERS (default: 2× CPU cores, min 1). Cap by batch size.
const DEFAULT_WORKERS = Math.max(1, (os.cpus().length || 4) * 2);

// In-memory cache: text -> base64 image (skip when request has options, e.g. lineWidth)
const cache = new Map();

// Create a fresh worker pool for one batch. Caller must terminate these workers when done.
// Using per-request pools avoids concurrent batches killing each other's workers.
function createWorkerPool(count) {
  const wanted = process.env.HANDWRITING_WORKERS ? Math.max(1, parseInt(process.env.HANDWRITING_WORKERS, 10)) : DEFAULT_WORKERS;
  const numWorkers = Math.min(count, wanted);
  const pool = [];
  for (let i = 0; i < numWorkers; i++) {
    const w = new Worker(path.join(__dirname, "worker-node.js"), {
      workerData: { handwrittenPath: HANDWRITTEN_PATH },
    });
    pool.push(w);
  }
  return pool;
}

function log(level, msg, ...args) {
  const ts = new Date().toISOString();
  console.log(`[${ts}] [${level}] ${msg}`, ...args);
}

// Single /generate: use cache if no options, else call handwritten directly
async function handleGenerate(body) {
  const { text, options = {} } = body;
  if (!text || typeof text !== "string") {
    return { status: 400, body: { error: "Missing or invalid 'text' field" } };
  }
  const hasOptions = options && Object.keys(options).length > 0;
  if (!hasOptions && cache.has(text)) {
    return { status: 200, body: { image: cache.get(text) } };
  }
  const start = Date.now();
  try {
    const handwritten = require(HANDWRITTEN_PATH);
    const base64 = await handwritten(text, { outputType: "png/b64", ...options });
    const result = Array.isArray(base64) ? base64[0] : base64;
    if (!hasOptions) cache.set(text, result);
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
  for (const t of texts) {
    if (typeof t !== "string") {
      return { status: 400, body: { error: "All items in 'texts' must be strings" } };
    }
  }
  const options = batchOptions && typeof batchOptions === "object" ? batchOptions : undefined;
  const hasOptions = options && Object.keys(options).length > 0;

  const startTime = Date.now();
  const pool = createWorkerPool(texts.length);
  const numWorkers = pool.length;
  log("INFO", `Batch: start count=${texts.length} workers=${numWorkers}`);

  const resolvers = new Array(texts.length).fill(null);
  const promises = texts.map((text, index) => {
    return new Promise((resolve, reject) => {
      resolvers[index] = { resolve, reject };
      // Cache hit (only when no options) – resolve immediately, do not send to worker
      if (!hasOptions && cache.has(text)) {
        setImmediate(() => {
          if (resolvers[index]) {
            resolvers[index].resolve(cache.get(text));
            resolvers[index] = null;
          }
        });
        return;
      }
      // Cache miss: send to worker (round-robin)
      const worker = pool[index % numWorkers];
      worker.postMessage({ id: index, text, options });
    });
  });

  const handler = (msg) => {
    const { id, success, image, error } = msg;
    const r = resolvers[id];
    if (!r) return;
    resolvers[id] = null;
    if (success) {
      if (!hasOptions) cache.set(texts[id], image);
      r.resolve(image);
    } else {
      r.reject(new Error(error));
    }
  };
  pool.forEach((w) => w.on("message", handler));

  let images;
  try {
    images = await Promise.all(promises);
  } catch (e) {
    log("ERROR", "Batch failed:", e.message);
    return { status: 500, body: { error: e.message } };
  } finally {
    pool.forEach((w) => w.off("message", handler));
    pool.forEach((w) => w.terminate());
  }

  const elapsed = Date.now() - startTime;
  log("INFO", `Batch: done count=${texts.length} elapsed=${elapsed} ms avg=${(elapsed / texts.length).toFixed(0)} ms/image workers=${numWorkers}`);
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
  log("INFO", `Handwriting service (Node, workers+cache) listening on http://localhost:${PORT}`);
  log("INFO", `Worker pool: ${process.env.HANDWRITING_WORKERS ? process.env.HANDWRITING_WORKERS + " (from HANDWRITING_WORKERS)" : DEFAULT_WORKERS + " (default 2×CPU, set HANDWRITING_WORKERS to override)"}`);
  log("INFO", "Endpoints: POST /generate, POST /generate-batch");
});
