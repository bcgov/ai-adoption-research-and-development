import { Camunda8 } from '@camunda8/sdk';
import axios, { AxiosResponse } from 'axios';
import type { WorkflowVariables, HttpResponse, ZeebeJob } from '../src/types';

const camunda = new Camunda8();
const zbc = camunda.getZeebeGrpcApiClient();

/**
 * Worker for submitting documents to Azure Document Intelligence OCR API.
 * Equivalent to n8n's "Submit to Azure OCR" HTTP Request node.
 */
zbc.createWorker<WorkflowVariables>({
  taskType: 'submit-to-azure-ocr',
  taskHandler: async (job: Readonly<ZeebeJob<WorkflowVariables>>) => {
    const endpoint = process.env.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT;
    const apiKey = process.env.AZURE_DOCUMENT_INTELLIGENCE_API_KEY;
    const contentType = job.variables.contentType || 'application/pdf';
    const binaryData = job.variables.binaryData;
    
    if (!endpoint || !apiKey) {
      throw new Error('Azure Document Intelligence credentials not configured. Set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and AZURE_DOCUMENT_INTELLIGENCE_API_KEY environment variables.');
    }
    
    if (!binaryData || typeof binaryData !== 'string') {
      throw new Error('No binary data available for OCR submission');
    }
    
    // Build URL
    const url = `${endpoint}/documentModels/prebuilt-layout:analyze?api-version=2024-11-30&features=keyValuePairs`;
    
    console.log(`[SubmitToAzureOCR] Submitting document to Azure OCR: ${url}`);
    console.log(`[SubmitToAzureOCR] Content-Type: ${contentType}, Data size: ${binaryData.length} bytes`);
    
    try {
      // Decode base64 to binary
      const fileBuffer = Buffer.from(binaryData, 'base64');
      
      // Make HTTP POST request
      const response: AxiosResponse = await axios.post(url, fileBuffer, {
        headers: {
          'api-key': apiKey,
          'Content-Type': contentType
        },
        maxContentLength: Infinity,
        maxBodyLength: Infinity
      });
      
      // Extract response details
      const statusCode = response.status;
      const apimRequestId = response.headers['apim-request-id'] || 
                         response.headers['Apim-Request-Id'] || 
                         response.headers['APIM-Request-Id'] || 
                         null;
      
      console.log(`[SubmitToAzureOCR] Azure OCR submission response: Status=${statusCode}, APIM-Request-ID=${apimRequestId}`);
      
      const httpResponse: HttpResponse = {
        statusCode: statusCode,
        headers: response.headers as Record<string, string | string[]>,
        apimRequestId: apimRequestId as string | undefined
      };
      
      // Return variables
      return job.complete({
        httpResponse: JSON.stringify(httpResponse),
        statusCode: statusCode,
        apimRequestId: apimRequestId || ''
      });
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error(`[SubmitToAzureOCR] Error submitting to Azure OCR: ${errorMessage}`);
      return job.fail(errorMessage);
    }
  },
  loglevel: 'INFO'
});

console.log('Submit to Azure OCR worker started. Waiting for tasks...');

