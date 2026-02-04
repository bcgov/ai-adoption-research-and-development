/**
 * Temporal Worker for OCR Workflow
 * Registers workflows and activities, connects to Temporal server
 */

import { NativeConnection, Worker } from '@temporalio/worker';
import * as activities from './activities';
// Workflows are automatically discovered via workflowsPath in Worker.create()

async function run() {
  // Load environment variables
  require('dotenv').config();

  const address = process.env.TEMPORAL_ADDRESS || 'localhost:7233';
  const namespace = process.env.TEMPORAL_NAMESPACE || 'default';
  const taskQueue = process.env.TEMPORAL_TASK_QUEUE || 'ocr-processing';

  console.log(`[Worker] Connecting to Temporal at ${address} (namespace: ${namespace})`);
  console.log(`[Worker] Task queue: ${taskQueue}`);

  // Create connection to Temporal server
  const connection = await NativeConnection.connect({
    address,
    // TLS configuration can be added here if needed
  });

  // Create worker
  const worker = await Worker.create({
    connection,
    namespace,
    workflowsPath: require.resolve('./workflow'),
    activities,
    taskQueue,
  });

  console.log('[Worker] Worker created and ready');
  console.log('[Worker] Listening for tasks on queue:', taskQueue);

  // Run worker (this will block until worker is shut down)
  await worker.run();
  console.log('[Worker] Worker stopped');
}

run().catch((err) => {
  console.error('[Worker] Fatal error:', err);
  process.exit(1);
});

