// Worker script for parallel handwriting generation
import handwritten from "npm:handwritten.js";

// Process messages sequentially per worker to ensure correct order
// This prevents race conditions while still allowing parallel processing across workers
let processingQueue: Array<{ id: number; text: string }> = [];
let isProcessing = false;

async function processQueue() {
  if (isProcessing || processingQueue.length === 0) {
    return;
  }
  
  isProcessing = true;
  while (processingQueue.length > 0) {
    const { id, text } = processingQueue.shift()!;
    try {
      const base64 = await handwritten(text, { outputType: 'png/b64' });
      self.postMessage({ id, success: true, image: base64 });
    } catch (error: any) {
      self.postMessage({ id, success: false, error: error.message });
    }
  }
  isProcessing = false;
}

// Listen for messages from main thread
self.onmessage = (e: MessageEvent) => {
  const { id, text } = e.data;
  processingQueue.push({ id, text });
  processQueue();
};
