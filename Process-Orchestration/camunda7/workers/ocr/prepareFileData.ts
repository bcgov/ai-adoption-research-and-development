import { Variables } from 'camunda-external-task-client-js';
import * as path from 'path';
import type { ExternalTaskHandlerArgs, WebhookBody, WorkflowVariables } from '../../src/types';
import client from '../client';

/**
 * Worker for preparing file data for Azure OCR.
 * Handles both webhook uploads and file reads from disk.
 */
client.subscribe(
  'prepare-file-data',
  async ({ task, taskService }: ExternalTaskHandlerArgs) => {
    const {
      filePath,
      webhookBody,
      webhookHeaders,
      fileContent,
      binaryData,
      fileName: inputFileName,
      contentType: inputContentType,
      fileType: inputFileType
    } = task.variables.getAll<WorkflowVariables>();

    console.log('[PrepareFileData] Preparing file data for Azure OCR');

    try {
      let fileName = inputFileName || 'document';
      let fileType: 'pdf' | 'image' = inputFileType || 'pdf';
      let contentType = inputContentType || 'application/pdf';
      let binaryDataLocal: string | null = null;

      let webhookBodyObj: WebhookBody | null = null;
      let webhookHeadersObj: Record<string, string> = {};

      // If binaryData already provided (Bytes arrives as Buffer), prefer it
      if (binaryData) {
        if (Buffer.isBuffer(binaryData)) {
          binaryDataLocal = binaryData.toString('base64');
        } else if (typeof binaryData === 'string') {
          binaryDataLocal = binaryData;
        }
      } else if (webhookBody) {
        webhookBodyObj =
          typeof webhookBody === 'string'
            ? (JSON.parse(webhookBody) as WebhookBody)
            : (webhookBody as WebhookBody);
      }

      if (webhookHeaders) {
        webhookHeadersObj =
          typeof webhookHeaders === 'string'
            ? (JSON.parse(webhookHeaders) as Record<string, string>)
            : (webhookHeaders as Record<string, string>);
      }

      if (!binaryDataLocal && webhookBodyObj) {
        const contentDisposition =
          webhookHeadersObj['content-disposition'] || webhookHeadersObj['Content-Disposition'] || '';
        const contentTypeHeader =
          webhookHeadersObj['content-type'] || webhookHeadersObj['Content-Type'] || '';

        if (contentDisposition) {
          const filenameMatch =
            contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
          if (filenameMatch && filenameMatch[1]) {
            fileName = filenameMatch[1].replace(/['"]/g, '');
          }
        }

        if (webhookBodyObj.content_type) {
          contentType = webhookBodyObj.content_type;
        } else if (contentTypeHeader) {
          contentType = contentTypeHeader.split(';')[0].trim();
        }

        if (webhookBodyObj.file) {
          binaryDataLocal = webhookBodyObj.file;
          fileName = webhookBodyObj.original_filename || webhookBodyObj.filename || fileName;
          fileType = (webhookBodyObj.file_type as 'pdf' | 'image') || 'pdf';
        } else if (webhookBodyObj.data) {
          binaryDataLocal = webhookBodyObj.data;
        }
      } else if (fileContent) {
        binaryDataLocal = fileContent;
        const filePathToUse = filePath || '/data/input.pdf';
        fileName = path.basename(filePathToUse);
      }

      const lowerFileName = fileName.toLowerCase();
      if (contentType.includes('pdf') || lowerFileName.endsWith('.pdf')) {
        fileType = 'pdf';
        contentType = 'application/pdf';
      } else if (
        contentType.includes('image') ||
        lowerFileName.match(/\.(jpg|jpeg|png|gif|bmp|tiff|webp)$/i)
      ) {
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

      if (!binaryDataLocal) {
        throw new Error(
          'No file data found. Please upload a file via manual trigger or send file data via webhook.'
        );
      }

      console.log(
        `[PrepareFileData] Prepared file: ${fileName}, type: ${fileType}, contentType: ${contentType}`
      );

      const variables = new Variables();
      variables.set('fileName', fileName);
      variables.set('fileType', fileType);
      variables.set('contentType', contentType);

      await taskService.complete(task, variables);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error(`[PrepareFileData] Error preparing file data: ${errorMessage}`);
      await taskService.handleFailure(task, errorMessage, 0, 0);
    }
  }
);

console.log('[OCR] Prepare File Data worker started.');




