import { Camunda8 } from '@camunda8/sdk';
import axios from 'axios';
import type { WorkflowVariables, OCRResponse, ZeebeJob } from '../src/types';

const camunda = new Camunda8();
const zbc = camunda.getZeebeGrpcApiClient();

/**
 * Worker for polling Azure Document Intelligence for OCR results.
 * Equivalent to n8n's "Poll OCR Results" HTTP Request node.
 */
zbc.createWorker<WorkflowVariables>({
  taskType: 'poll-ocr-results',
  taskHandler: async (job: Readonly<ZeebeJob<WorkflowVariables>>) => {
    const endpoint = process.env.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT;
    const apiKey = process.env.AZURE_DOCUMENT_INTELLIGENCE_API_KEY;
    const apimRequestId = job.variables.apimRequestId;
    
    if (!endpoint || !apiKey) {
      throw new Error('Azure Document Intelligence credentials not configured. Set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and AZURE_DOCUMENT_INTELLIGENCE_API_KEY environment variables.');
    }
    
    if (!apimRequestId || typeof apimRequestId !== 'string') {
      throw new Error('APIM Request ID not available for polling');
    }
    
    // Build URL
    const url = `${endpoint}/documentModels/prebuilt-layout/analyzeResults/${apimRequestId}?api-version=2024-11-30`;
    
    console.log(`[PollOCRResults] Polling OCR results: ${url}`);
    
    try {
      // Make HTTP GET request
      const response = await axios.get<OCRResponse>(url, {
        headers: {
          'api-key': apiKey
        }
      });
      
      // Extract response body
      const responseBody = response.data;
      
      if (!responseBody) {
        throw new Error('Empty response from Azure OCR polling endpoint');
      }
      
      const status = responseBody.status || 'unknown';
      console.log(`[PollOCRResults] OCR polling response: Status=${status}`);
      
      // Return variables
      return job.complete({
        ocrResponse: JSON.stringify(responseBody),
        ocrStatus: status
      });
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error(`[PollOCRResults] Error polling OCR results: ${errorMessage}`);
      return job.fail(errorMessage);
    }
  },
  loglevel: 'INFO'
});

console.log('Poll OCR Results worker started. Waiting for tasks...');

