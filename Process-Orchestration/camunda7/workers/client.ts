import 'dotenv/config';
import { Client, logger } from 'camunda-external-task-client-js';
import { CAMUNDA_ENGINE_URL, getCamundaAuth } from '../src/camunda';

const fallbackWorkerId = `ocr-worker-${Math.random().toString(36).slice(2, 8)}`;

const baseUrl = CAMUNDA_ENGINE_URL;
const camundaAuth = getCamundaAuth();

export const client = new Client({
  baseUrl,
  workerId: process.env.CAMUNDA_WORKER_ID || fallbackWorkerId,
  asyncResponseTimeout: 10000,
  maxTasks: 1,
  use: logger,
  ...(camundaAuth ? { basicAuth: camundaAuth } : {})
});

client.on('poll:error', (err: unknown) => {
  const message = err instanceof Error ? err.message : String(err);
  console.error('[Camunda Client] Poll error:', message);
});

client.on('subscribe:error', (err: unknown) => {
  const message = err instanceof Error ? err.message : String(err);
  console.error('[Camunda Client] Subscribe error:', message);
});

export default client;


