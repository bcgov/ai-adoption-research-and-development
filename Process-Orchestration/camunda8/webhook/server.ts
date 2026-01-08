import 'dotenv/config';
import express, { Request, Response } from 'express';
import multer from 'multer';
import { Camunda8 } from '@camunda8/sdk';
import type { WebhookBody } from '../src/types';

const app = express();
const camunda = new Camunda8();
const zbc = camunda.getZeebeGrpcApiClient();

const PORT = process.env.WEBHOOK_PORT ? parseInt(process.env.WEBHOOK_PORT, 10) : 3000;

// Configure multer for multipart/form-data file uploads (memory storage)
const upload = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: 50 * 1024 * 1024 // 50MB limit
  }
});

// Middleware to parse binary data (for direct binary uploads)
app.use(express.raw({ 
  type: ['application/pdf', 'image/jpeg', 'image/png', 'application/octet-stream'], 
  limit: '50mb' 
}));
app.use(express.json({ limit: '50mb' }));

// Health check endpoint
app.get('/health', (_req: Request, res: Response) => {
  res.json({ status: 'ok', service: 'webhook-server' });
});

/**
 * REST endpoint for handling webhook file uploads.
 * Supports multiple upload formats:
 * 1. multipart/form-data (standard file upload with field name 'file')
 * 2. Direct binary upload (application/pdf, image/*, etc.)
 * 3. JSON with base64 encoded file
 * 
 * Starts a new Camunda 8 process instance.
 */
app.post('/ocr-upload', (req, res, next) => {
  // Handle multer errors
  upload.single('file')(req, res, (err) => {
    if (err) {
      console.error('[Webhook] Multer error:', err);
      if (err instanceof multer.MulterError) {
        if (err.code === 'LIMIT_FILE_SIZE') {
          res.status(400).json({
            success: false,
            error: 'File too large. Maximum size is 50MB.'
          });
          return;
        }
        res.status(400).json({
          success: false,
          error: `File upload error: ${err.message}`
        });
        return;
      }
      res.status(500).json({
        success: false,
        error: `Upload error: ${err.message}`
      });
      return;
    }
    next();
  });
}, async (req: Request, res: Response): Promise<void> => {
  try {
    // Debug logging
    console.log(`[Webhook] Request received - Content-Type: ${req.headers['content-type']}`);
    console.log(`[Webhook] req.file:`, req.file ? `Present (${req.file.originalname}, ${req.file.size} bytes)` : 'Not present');
    console.log(`[Webhook] req.body type:`, typeof req.body, Buffer.isBuffer(req.body) ? '(Buffer)' : '');
    
    // Extract headers
    const headers: Record<string, string> = {};
    Object.keys(req.headers).forEach(key => {
      const value = req.headers[key];
      if (value) {
        headers[key.toLowerCase()] = Array.isArray(value) ? value[0] : value;
      }
    });
    
    let webhookBody: WebhookBody;
    let base64Data: string;
    let fileSize = 0;
    
    // Handle multipart/form-data file upload (most common)
    if (req.file) {
      const file = req.file;
      base64Data = file.buffer.toString('base64');
      fileSize = file.size;
      
      // Extract file type from mimetype or extension
      const fileType = file.mimetype?.includes('pdf') ? 'pdf' 
        : file.mimetype?.includes('image') ? 'image' 
        : undefined;
      
      webhookBody = {
        file: base64Data,
        original_filename: file.originalname,
        filename: file.originalname,
        file_type: fileType,
        content_type: file.mimetype
      };
      
      console.log(`[Webhook] Received multipart file upload: ${file.originalname}, size: ${fileSize} bytes, type: ${file.mimetype}`);
    }
    // Handle binary file upload (direct binary POST)
    else if (Buffer.isBuffer(req.body)) {
      base64Data = req.body.toString('base64');
      fileSize = req.body.length;
      webhookBody = {
        data: base64Data
      };
      console.log(`[Webhook] Received binary file upload, size: ${fileSize} bytes`);
    }
    // Handle JSON with base64 file
    else if (req.body && typeof req.body === 'object' && 'file' in req.body) {
      const body = req.body as { file: string; original_filename?: string; filename?: string; file_type?: string; content_type?: string };
      base64Data = body.file;
      fileSize = Buffer.from(base64Data, 'base64').length;
      webhookBody = {
        file: base64Data,
        original_filename: body.original_filename,
        filename: body.filename,
        file_type: body.file_type,
        content_type: body.content_type
      };
      console.log(`[Webhook] Received JSON file upload, size: ${fileSize} bytes`);
    }
    // Check if it's multipart but file wasn't captured (wrong field name or multer error)
    else if (req.headers['content-type']?.includes('multipart/form-data')) {
      const errorMsg = 'Multipart/form-data detected but no file was captured. Make sure the field name is "file" and the file is included in the request.';
      console.error(`[Webhook] ${errorMsg}`);
      console.error(`[Webhook] req.body keys:`, req.body && typeof req.body === 'object' ? Object.keys(req.body) : 'N/A');
      res.status(400).json({
        success: false,
        error: errorMsg,
        hint: 'Use: curl -X POST http://localhost:3000/ocr-upload -F "file=@yourfile.pdf"'
      });
      return;
    }
    // Fallback: use body as-is (but this shouldn't happen for valid uploads)
    else {
      console.warn(`[Webhook] Unexpected request format. req.body:`, typeof req.body, req.body);
      webhookBody = req.body as WebhookBody || {};
      fileSize = req.body ? JSON.stringify(req.body).length : 0;
      console.log(`[Webhook] Received JSON body, size: ${fileSize} bytes`);
    }
    
    // Validate that we have file data
    if (!webhookBody.file && !webhookBody.data) {
      const errorMsg = 'No file data found in request. Please include a file in your upload.';
      console.error(`[Webhook] ${errorMsg}`);
      console.error(`[Webhook] webhookBody:`, JSON.stringify(webhookBody));
      res.status(400).json({
        success: false,
        error: errorMsg,
        hint: 'For multipart: curl -X POST http://localhost:3000/ocr-upload -F "file=@yourfile.pdf"'
      });
      return;
    }
    
    // Start process instance
    const result = await zbc.createProcessInstance({
      bpmnProcessId: 'azure-ocr-document-processing',
      variables: {
        webhookBody: JSON.stringify(webhookBody),
        webhookHeaders: JSON.stringify(headers),
        retryCount: 0  // Initialize retry count
      }
    });
    
    const processInstanceKey = result.processInstanceKey;
    console.log(`[Webhook] Started process instance: ${processInstanceKey}`);
    
    // Return response
    res.json({
      success: true,
      processInstanceKey: processInstanceKey,
      message: 'File uploaded and OCR process started',
      fileSize: fileSize
    });
    
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    console.error('[Webhook] Error processing webhook upload:', errorMessage);
    
    res.status(500).json({
      success: false,
      error: errorMessage
    });
  }
});

app.listen(PORT, () => {
  console.log(`Webhook server listening on port ${PORT}`);
  console.log(`Webhook endpoint: http://localhost:${PORT}/ocr-upload`);
  console.log(`Health check: http://localhost:${PORT}/health`);
  console.log(`\nSupported upload formats:`);
  console.log(`  1. multipart/form-data (field name: 'file')`);
  console.log(`  2. Direct binary (application/pdf, image/*, etc.)`);
  console.log(`  3. JSON with base64 encoded file`);
});





