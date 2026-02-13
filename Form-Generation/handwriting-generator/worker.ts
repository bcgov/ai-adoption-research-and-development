// Worker script for parallel handwriting generation
import handwritten from "npm:handwritten.js";

function log(msg: string, ...args: unknown[]) {
  const ts = new Date().toISOString();
  console.log(`[${ts}] [Worker] ${msg}`, ...args);
}

let processingQueue: Array<{ id: number; text: string }> = [];
let isProcessing = false;

async function processQueue() {
  if (isProcessing || processingQueue.length === 0) {
    return;
  }
  
  isProcessing = true;
  while (processingQueue.length > 0) {
    const { id, text, options } = processingQueue.shift()!;
    const preview = text.length > 25 ? text.slice(0, 22) + "..." : text;
    const start = Date.now();
    try {
      const base64 = await handwritten(text, { outputType: 'png/b64', ...options });
      const elapsed = Date.now() - start;
      log(`id=${id} done in ${elapsed} ms (${text.length} chars) "${preview}"`);
      self.postMessage({ id, success: true, image: base64 });
    } catch (error: any) {
      log(`id=${id} FAILED after ${Date.now() - start} ms: ${error.message} "${preview}"`);
      self.postMessage({ id, success: false, error: error.message });
    }
  }
  isProcessing = false;
}

self.onmessage = (e: MessageEvent) => {
  const { id, text, options } = e.data;
  processingQueue.push({ id, text, options: options ?? {} });
  processQueue();
};
