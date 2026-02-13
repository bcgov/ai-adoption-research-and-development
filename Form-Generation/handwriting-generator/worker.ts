// Worker script for parallel handwriting generation
import handwritten from "npm:handwritten.js";

// Listen for messages from main thread
self.onmessage = async (e: MessageEvent) => {
  const { id, text } = e.data;
  try {
    const base64 = await handwritten(text, { outputType: 'png/b64' });
    self.postMessage({ id, success: true, image: base64 });
  } catch (error: any) {
    self.postMessage({ id, success: false, error: error.message });
  }
};
