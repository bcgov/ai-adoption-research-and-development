import { Variables } from 'camunda-external-task-client-js';
import axios, { AxiosResponse } from 'axios';
import type { ExternalTaskHandlerArgs, HttpResponse, WorkflowVariables } from '../../src/types';
import client from '../client';

/**
 * Worker for submitting documents to Azure Document Intelligence OCR API.
 * Equivalent to n8n's "Submit to Azure OCR" HTTP Request node.
 */
client.subscribe(
  'submit-to-azure-ocr',
  async ({ task, taskService }: ExternalTaskHandlerArgs) => {
    const { contentType, binaryData } = task.variables.getAll<WorkflowVariables>();
    const endpoint = process.env.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT;
    const apiKey = process.env.AZURE_DOCUMENT_INTELLIGENCE_API_KEY;
    const contentTypeToUse = contentType || 'application/pdf';

    if (!endpoint || !apiKey) {
      throw new Error(
        'Azure Document Intelligence credentials not configured. Set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and AZURE_DOCUMENT_INTELLIGENCE_API_KEY environment variables.'
      );
    }

    let binaryBase64: string | undefined;
    if (Buffer.isBuffer(binaryData)) {
      binaryBase64 = binaryData.toString('base64');
    } else if (typeof binaryData === 'string') {
      binaryBase64 = binaryData;
    }

    if (!binaryBase64) {
      throw new Error('No binary data available for OCR submission');
    }

    const url = `${endpoint}/documentModels/prebuilt-layout:analyze?api-version=2024-11-30&features=keyValuePairs`;

    console.log(`[SubmitToAzureOCR] Submitting document to Azure OCR: ${url}`);
    console.log(`[SubmitToAzureOCR] Content-Type: ${contentTypeToUse}, Data size: ${binaryBase64.length} bytes`);

    try {
      const fileBuffer = Buffer.from(binaryBase64, 'base64');

      const response: AxiosResponse = await axios.post(url, fileBuffer, {
        headers: {
          'api-key': apiKey,
          'Content-Type': contentTypeToUse
        },
        maxContentLength: Infinity,
        maxBodyLength: Infinity
      });

      const statusCode = response.status;
      const apimRequestId =
        response.headers['apim-request-id'] ||
        response.headers['Apim-Request-Id'] ||
        response.headers['APIM-Request-Id'] ||
        null;

      console.log(
        `[SubmitToAzureOCR] Azure OCR submission response: Status=${statusCode}, APIM-Request-ID=${apimRequestId}`
      );

      const httpResponse: HttpResponse = {
        statusCode,
        headers: response.headers as Record<string, string | string[]>,
        apimRequestId: apimRequestId as string | undefined
      };

      const variables = new Variables();
      variables.set('httpResponse', JSON.stringify(httpResponse));
      variables.set('statusCode', statusCode);
      variables.set('apimRequestId', apimRequestId || '');

      await taskService.complete(task, variables);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error(`[SubmitToAzureOCR] Error submitting to Azure OCR: ${errorMessage}`);
      await taskService.handleFailure(task, errorMessage, 0, 0);
    }
  }
);

console.log('[OCR] Submit to Azure OCR worker started.');




