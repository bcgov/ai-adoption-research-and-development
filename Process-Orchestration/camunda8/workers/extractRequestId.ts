import { Camunda8 } from '@camunda8/sdk';
import type { WorkflowVariables, HttpResponse, ZeebeJob } from '../src/types';

const camunda = new Camunda8();
const zbc = camunda.getZeebeGrpcApiClient();

/**
 * Worker for extracting APIM request ID from HTTP response.
 */
zbc.createWorker<WorkflowVariables>({
  taskType: 'extract-request-id',
  taskHandler: async (job: Readonly<ZeebeJob<WorkflowVariables>>) => {
    const { httpResponse } = job.variables;
    
    console.log('[ExtractRequestId] Extracting request ID from HTTP response');
    
    try {
      // Parse HTTP response
      const httpResponseObj: HttpResponse = typeof httpResponse === 'string' 
        ? JSON.parse(httpResponse) as HttpResponse
        : httpResponse as HttpResponse;
      
      const statusCode = httpResponseObj?.statusCode || null;
      const headers = httpResponseObj?.headers || {};
      
      let apimRequestId: string | null = null;
      
      // Extract apim-request-id from headers (case-insensitive)
      if (headers) {
        const headerValue = headers['apim-request-id'] || 
                           headers['Apim-Request-Id'] || 
                           headers['APIM-Request-Id'];
        
        if (headerValue) {
          apimRequestId = Array.isArray(headerValue) ? headerValue[0] : headerValue;
        }
      }
      
      console.log(`[ExtractRequestId] Status Code: ${statusCode}, APIM Request ID: ${apimRequestId || 'not found'}`);
      
      return job.complete({
        statusCode: statusCode ?? 0,
        apimRequestId: apimRequestId || '',
        status: 'submitted'
      });
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error(`[ExtractRequestId] Error extracting request ID: ${errorMessage}`);
      return job.fail(errorMessage);
    }
  },
  loglevel: 'INFO'
});

console.log('Extract Request ID worker started. Waiting for tasks...');

