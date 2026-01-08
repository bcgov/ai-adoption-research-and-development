import { Camunda8 } from '@camunda8/sdk';
import * as path from 'path';
import type { WorkflowVariables, WebhookBody, ZeebeJob } from '../src/types';

const camunda = new Camunda8();
const zbc = camunda.getZeebeGrpcApiClient();

/**
 * Worker for preparing file data for Azure OCR.
 * Handles both webhook uploads and file reads from disk.
 */
zbc.createWorker<WorkflowVariables>({
  taskType: 'prepare-file-data',
  taskHandler: async (job: Readonly<ZeebeJob<WorkflowVariables>>) => {
    const { filePath, webhookBody, webhookHeaders, fileContent } = job.variables;
    
    console.log('[PrepareFileData] Preparing file data for Azure OCR');
    
    try {
      let fileName = 'document';
      let fileType: 'pdf' | 'image' = 'pdf';
      let contentType = 'application/pdf';
      let binaryData: string | null = null;
      
      // Parse webhook data if present
      let webhookBodyObj: WebhookBody | null = null;
      let webhookHeadersObj: Record<string, string> = {};
      
      if (webhookBody) {
        webhookBodyObj = typeof webhookBody === 'string' 
          ? JSON.parse(webhookBody) as WebhookBody
          : webhookBody as WebhookBody;
      }
      
      if (webhookHeaders) {
        webhookHeadersObj = typeof webhookHeaders === 'string' 
          ? JSON.parse(webhookHeaders) as Record<string, string>
          : webhookHeaders as Record<string, string>;
      }
      
      // Handle webhook input
      if (webhookBodyObj) {
        // Extract from headers (fallback if not in webhookBody)
        const contentDisposition = webhookHeadersObj['content-disposition'] || 
                                   webhookHeadersObj['Content-Disposition'] || '';
        const contentTypeHeader = webhookHeadersObj['content-type'] || 
                                  webhookHeadersObj['Content-Type'] || '';
        
        if (contentDisposition) {
          const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
          if (filenameMatch && filenameMatch[1]) {
            fileName = filenameMatch[1].replace(/['"]/g, '');
          }
        }
        
        // Prioritize content_type from webhookBody over headers
        if (webhookBodyObj.content_type) {
          contentType = webhookBodyObj.content_type;
        } else if (contentTypeHeader) {
          contentType = contentTypeHeader.split(';')[0].trim();
        }
        
        // Handle base64 file data
        if (webhookBodyObj.file) {
          binaryData = webhookBodyObj.file;
          fileName = webhookBodyObj.original_filename || webhookBodyObj.filename || fileName;
          fileType = (webhookBodyObj.file_type as 'pdf' | 'image') || 'pdf';
        } else if (webhookBodyObj.data) {
          binaryData = webhookBodyObj.data;
        }
      } else if (fileContent) {
        // File read from disk
        binaryData = fileContent;
        const filePathToUse = filePath || '/data/input.pdf';
        fileName = path.basename(filePathToUse);
      }
      
      // Determine file type
      const lowerFileName = fileName.toLowerCase();
      if (contentType.includes('pdf') || lowerFileName.endsWith('.pdf')) {
        fileType = 'pdf';
        contentType = 'application/pdf';
      } else if (contentType.includes('image') || lowerFileName.match(/\.(jpg|jpeg|png|gif|bmp|tiff|webp)$/i)) {
        fileType = 'image';
        if (!contentType || contentType === 'application/pdf') {
          if (lowerFileName.endsWith('.png')) {
            contentType = 'image/png';
          } else if (lowerFileName.match(/\.(jpg|jpeg)$/i)) {
            contentType = 'image/jpeg';
          } else {
            contentType = contentType || 'image/jpeg';
          }
        }
      }
      
      if (!binaryData) {
        throw new Error('No file data found. Please upload a file via manual trigger or send file data via webhook.');
      }
      
      console.log(`[PrepareFileData] Prepared file: ${fileName}, type: ${fileType}, contentType: ${contentType}`);
      
      return job.complete({
        fileName: fileName,
        fileType: fileType,
        contentType: contentType,
        binaryData: binaryData
      });
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error(`[PrepareFileData] Error preparing file data: ${errorMessage}`);
      return job.fail(errorMessage);
    }
  },
  loglevel: 'INFO'
});

console.log('Prepare File Data worker started. Waiting for tasks...');

