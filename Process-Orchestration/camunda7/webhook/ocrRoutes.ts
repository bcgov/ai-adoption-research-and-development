import { Router, Request, Response, NextFunction } from 'express';
import axios from 'axios';
import multer from 'multer';
import { CAMUNDA_ENGINE_URL, getCamundaAuth } from '../src/camunda';
import type { WebhookBody } from '../src/types';

const router = Router();

// Create axios client for Camunda API
const camundaClient = axios.create({
  baseURL: CAMUNDA_ENGINE_URL,
  auth: getCamundaAuth()
});

// Configure multer for multipart/form-data file uploads (memory storage)
const upload = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: 50 * 1024 * 1024 // 50MB limit
  }
});

/**
 * POST /ocr-upload
 * REST endpoint for handling OCR file uploads.
 * Supports multiple upload formats:
 * 1. multipart/form-data (standard file upload with field name 'file')
 * 2. Direct binary upload (application/pdf, image/*, etc.)
 * 3. JSON with base64 encoded file
 *
 * Starts a new Camunda 7 process instance.
 */
router.post(
  '/ocr-upload',
  (req: Request, res: Response, next: NextFunction) => {
    upload.single('file')(req, res, (err) => {
      if (err) {
        console.error('[OCR Webhook] Multer error:', err);
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
  },
  async (req: Request, res: Response): Promise<void> => {
    try {
      console.log(`[OCR Webhook] Request received - Content-Type: ${req.headers['content-type']}`);
      console.log(
        `[OCR Webhook] req.file:`,
        req.file ? `Present (${req.file.originalname}, ${req.file.size} bytes)` : 'Not present'
      );
      console.log(
        `[OCR Webhook] req.body type:`,
        typeof req.body,
        Buffer.isBuffer(req.body) ? '(Buffer)' : ''
      );

      const headers: Record<string, string> = {};
      Object.keys(req.headers).forEach((key) => {
        const value = req.headers[key];
        if (value) {
          headers[key.toLowerCase()] = Array.isArray(value) ? value[0] : value;
        }
      });

      let webhookBody: WebhookBody;
      let base64Data: string | null = null;
      let fileSize = 0;
      let fileName = 'document';
      let fileType: 'pdf' | 'image' | undefined;
      let contentType: string | undefined;

      if (req.file) {
        const file = req.file;
        base64Data = file.buffer.toString('base64');
        fileSize = file.size;

        fileName = file.originalname;
        fileType = file.mimetype?.includes('pdf')
          ? 'pdf'
          : file.mimetype?.includes('image')
            ? 'image'
            : undefined;
        contentType = file.mimetype;

        webhookBody = {
          file: base64Data,
          original_filename: fileName,
          filename: fileName,
          file_type: fileType,
          content_type: contentType
        };

        console.log(
          `[OCR Webhook] Received multipart file upload: ${file.originalname}, size: ${fileSize} bytes, type: ${file.mimetype}`
        );
      } else if (Buffer.isBuffer(req.body)) {
        base64Data = req.body.toString('base64');
        fileSize = req.body.length;
        fileType = 'pdf';
        contentType = req.headers['content-type'] || 'application/octet-stream';
        webhookBody = {
          data: base64Data
        };
        console.log(`[OCR Webhook] Received binary file upload, size: ${fileSize} bytes`);
      } else if (req.body && typeof req.body === 'object' && 'file' in req.body) {
        const body = req.body as {
          file: string;
          original_filename?: string;
          filename?: string;
          file_type?: string;
          content_type?: string;
        };
        base64Data = body.file;
        fileSize = Buffer.from(base64Data, 'base64').length;
        fileName = body.filename || body.original_filename || fileName;
        fileType = (body.file_type as 'pdf' | 'image' | undefined) || fileType;
        contentType = body.content_type || contentType;
        webhookBody = {
          file: base64Data,
          original_filename: body.original_filename,
          filename: body.filename,
          file_type: body.file_type,
          content_type: body.content_type
        };
        console.log(`[OCR Webhook] Received JSON file upload, size: ${fileSize} bytes`);
      } else if (req.headers['content-type']?.includes('multipart/form-data')) {
        const errorMsg =
          'Multipart/form-data detected but no file was captured. Make sure the field name is "file" and the file is included in the request.';
        console.error(`[OCR Webhook] ${errorMsg}`);
        console.error(
          `[OCR Webhook] req.body keys:`,
          req.body && typeof req.body === 'object' ? Object.keys(req.body) : 'N/A'
        );
        res.status(400).json({
          success: false,
          error: errorMsg,
          hint: 'Use: curl -X POST http://localhost:3000/ocr-upload -F "file=@yourfile.pdf"'
        });
        return;
      } else {
        console.warn(`[OCR Webhook] Unexpected request format. req.body:`, typeof req.body, req.body);
        webhookBody = (req.body as WebhookBody) || {};
        fileSize = req.body ? JSON.stringify(req.body).length : 0;
        console.log(`[OCR Webhook] Received JSON body, size: ${fileSize} bytes`);
      }

      if (!webhookBody.file && !webhookBody.data) {
        const errorMsg = 'No file data found in request. Please include a file in your upload.';
        console.error(`[OCR Webhook] ${errorMsg}`);
        console.error(`[OCR Webhook] webhookBody:`, JSON.stringify(webhookBody));
        res.status(400).json({
          success: false,
          error: errorMsg,
          hint: 'For multipart: curl -X POST http://localhost:3000/ocr-upload -F "file=@yourfile.pdf"'
        });
        return;
      }

      if (!base64Data) {
        const errorMsg = 'No file data extracted from upload.';
        console.error(`[OCR Webhook] ${errorMsg}`);
        res.status(400).json({
          success: false,
          error: errorMsg
        });
        return;
      }

      const startResponse = await camundaClient.post(
        '/process-definition/key/azure-ocr-document-processing/start',
        {
          variables: {
            // Large payload in Bytes to avoid DB string limits
            binaryData: {
              // Camunda expects base64 string for Bytes via REST
              value: base64Data,
              type: 'Bytes',
              valueInfo: {
                filename: fileName,
                mimeType: contentType || 'application/pdf'
              }
            },
            fileName: { value: fileName, type: 'String' },
            fileType: { value: fileType || 'pdf', type: 'String' },
            contentType: { value: contentType || 'application/pdf', type: 'String' },
            // Keep small metadata strings
            webhookBody: { value: JSON.stringify({ ...webhookBody, file: undefined, data: undefined }), type: 'String' },
            webhookHeaders: { value: JSON.stringify(headers), type: 'String' },
            retryCount: { value: 0, type: 'Long' },
            // ensure expression gateways see defined variables
            filePath: { value: '', type: 'String' }
          }
        }
      );

      const processInstanceId = startResponse.data?.id;
      console.log(`[OCR Webhook] Started process instance: ${processInstanceId}`);

      res.json({
        success: true,
        processInstanceId,
        message: 'File uploaded and OCR process started',
        fileSize
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error('[OCR Webhook] Error processing webhook upload:', errorMessage);
      if (axios.isAxiosError(error)) {
        console.error('[OCR Webhook] Camunda response:', error.response?.data);
      }

      res.status(500).json({
        success: false,
        error: errorMessage
      });
    }
  }
);

export default router;




