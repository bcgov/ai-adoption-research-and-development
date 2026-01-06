import 'dotenv/config';

// Start webhook server
import './webhook/server';

// Start all workers
import './workers/index';

console.log('Camunda 7 OCR Workflow - All services started');


