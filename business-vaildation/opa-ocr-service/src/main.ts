import express, { Express, Request, Response } from 'express';
import dotenv from 'dotenv';
import { OpaService } from './services/opa.service';
import { PolicyService } from './services/policy.service';
import { PolicyController } from './controllers/policy.controller';

// Load environment variables
dotenv.config();

const app: Express = express();
const port = process.env.PORT || 3001;

// Middleware
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Enable CORS
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept, Authorization');
  if (req.method === 'OPTIONS') {
    res.sendStatus(200);
  } else {
    next();
  }
});

// Initialize services
const opaService = new OpaService();
const policyService = new PolicyService(opaService);
const policyController = new PolicyController(policyService);

// Routes
app.get('/', (req: Request, res: Response) => {
  res.json({
    service: 'OPA OCR Service',
    version: '1.0.0',
    description: 'Open Policy Agent API service for post-OCR processing validation',
    endpoints: {
      evaluate: 'POST /api/policy/evaluate',
      policies: 'GET /api/policy/policies',
      health: 'GET /api/policy/health',
    },
  });
});

// Policy API routes
app.use('/api/policy', policyController.getRouter());

// Error handling middleware
app.use((err: Error, req: Request, res: Response, next: express.NextFunction) => {
  console.error('Unhandled error:', err);
  res.status(500).json({
    error: 'Internal server error',
    message: err.message,
  });
});

// Start server
app.listen(port, () => {
  console.log(`OPA OCR Service is running on: http://localhost:${port}`);
  console.log(`OPA Server URL: ${process.env.OPA_SERVER_URL || 'http://localhost:8181'}`);
  console.log(`Policies Directory: ${process.env.POLICIES_DIR || './policies'}`);
});

