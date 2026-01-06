import 'dotenv/config';
import express, { Request, Response } from 'express';

// Route modules
import ocrRoutes from './ocrRoutes';
import agentRoutes from './agentRoutes';

const app = express();
const PORT = process.env.WEBHOOK_PORT ? parseInt(process.env.WEBHOOK_PORT, 10) : 3000;

// Middleware for binary data (for direct binary uploads)
app.use(
  express.raw({
    type: ['application/pdf', 'image/jpeg', 'image/png', 'application/octet-stream'],
    limit: '50mb'
  })
);
app.use(express.json({ limit: '50mb' }));

// Health check endpoint
app.get('/health', (_req: Request, res: Response) => {
  res.json({ status: 'ok', service: 'camunda-webhook-server' });
});

// Register workflow routes
app.use(ocrRoutes);     // /ocr-upload
app.use(agentRoutes);   // /agent-chat, /agent-chat/status/:id

app.listen(PORT, () => {
  console.log('');
  console.log('='.repeat(50));
  console.log(`Webhook Server Running on port ${PORT}`);
  console.log('='.repeat(50));
  console.log('');
  console.log('Endpoints:');
  console.log('');
  console.log('  OCR Workflow:');
  console.log(`    POST http://localhost:${PORT}/ocr-upload`);
  console.log('');
  console.log('  GitHub Agent:');
  console.log(`    POST http://localhost:${PORT}/agent-chat`);
  console.log(`    GET  http://localhost:${PORT}/agent-chat/status/:id`);
  console.log('');
  console.log('  Health Check:');
  console.log(`    GET  http://localhost:${PORT}/health`);
  console.log('');
  console.log('='.repeat(50));
});
