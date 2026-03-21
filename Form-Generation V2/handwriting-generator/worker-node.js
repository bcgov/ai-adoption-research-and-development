"use strict";
/**
 * Worker thread: loads handwritten.js and processes (id, text, options) messages.
 * Processes one message at a time (queue) to avoid overwhelming the library.
 */

const { parentPort, workerData } = require("worker_threads");
const handwritten = require(workerData.handwrittenPath);

const queue = [];
let processing = false;

async function processQueue() {
  if (processing || queue.length === 0) return;
  processing = true;
  while (queue.length > 0) {
    const { id, text, options } = queue.shift();
    try {
      const base64 = await handwritten(text, { outputType: "png/b64", ...options });
      const image = Array.isArray(base64) ? base64[0] : base64;
      parentPort.postMessage({ id, success: true, image });
    } catch (e) {
      parentPort.postMessage({ id, success: false, error: e.message });
    }
  }
  processing = false;
}

parentPort.on("message", (msg) => {
  queue.push(msg);
  processQueue();
});
