import { Variables } from 'camunda-external-task-client-js';
import axios from 'axios';
import type { ExternalTaskHandlerArgs, OCRResponse, WorkflowVariables } from '../../src/types';
import client from '../client';

/**
 * Worker for polling Azure Document Intelligence for OCR results.
 * Equivalent to n8n's "Poll OCR Results" HTTP Request node.
 */
client.subscribe(
  'poll-ocr-results',
  async ({ task, taskService }: ExternalTaskHandlerArgs) => {
    const { apimRequestId } = task.variables.getAll<WorkflowVariables>();
    const endpoint = process.env.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT;
    const apiKey = process.env.AZURE_DOCUMENT_INTELLIGENCE_API_KEY;

    if (!endpoint || !apiKey) {
      throw new Error(
        'Azure Document Intelligence credentials not configured. Set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and AZURE_DOCUMENT_INTELLIGENCE_API_KEY environment variables.'
      );
    }

    if (!apimRequestId || typeof apimRequestId !== 'string') {
      throw new Error('APIM Request ID not available for polling');
    }

    const url = `${endpoint}/documentModels/prebuilt-layout/analyzeResults/${apimRequestId}?api-version=2024-11-30`;

    console.log(`[PollOCRResults] Polling OCR results: ${url}`);

    try {
      const response = await axios.get<OCRResponse>(url, {
        headers: {
          'api-key': apiKey
        }
      });

      const responseBody = response.data;

      if (!responseBody) {
        throw new Error('Empty response from Azure OCR polling endpoint');
      }

      const status = responseBody.status || 'unknown';
      console.log(`[PollOCRResults] OCR polling response: Status=${status}`);

      const variables = new Variables();
      // Only pass status; avoid persisting full payload to keep DB small
      variables.set('ocrStatus', status);

      await taskService.complete(task, variables);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error(`[PollOCRResults] Error polling OCR results: ${errorMessage}`);
      await taskService.handleFailure(task, errorMessage, 0, 0);
    }
  }
);

console.log('[OCR] Poll OCR Results worker started.');




