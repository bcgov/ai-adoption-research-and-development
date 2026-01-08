import { Variables } from 'camunda-external-task-client-js';
import type { ExternalTaskHandlerArgs, HttpResponse, WorkflowVariables } from '../../src/types';
import client from '../client';

/**
 * Worker for extracting APIM request ID from HTTP response.
 */
client.subscribe(
  'extract-request-id',
  async ({ task, taskService }: ExternalTaskHandlerArgs) => {
    const { httpResponse } = task.variables.getAll<WorkflowVariables>();

    console.log('[ExtractRequestId] Extracting request ID from HTTP response');

    try {
      const httpResponseObj: HttpResponse =
        typeof httpResponse === 'string'
          ? (JSON.parse(httpResponse) as HttpResponse)
          : (httpResponse as HttpResponse);

      const statusCode = httpResponseObj?.statusCode || null;
      const headers = httpResponseObj?.headers || {};

      let apimRequestId: string | null = null;

      if (headers) {
        const headerValue =
          (headers as Record<string, string | string[]>)['apim-request-id'] ||
          (headers as Record<string, string | string[]>)['Apim-Request-Id'] ||
          (headers as Record<string, string | string[]>)['APIM-Request-Id'];

        if (headerValue) {
          apimRequestId = Array.isArray(headerValue) ? headerValue[0] : headerValue;
        }
      }

      console.log(
        `[ExtractRequestId] Status Code: ${statusCode}, APIM Request ID: ${apimRequestId || 'not found'}`
      );

      const variables = new Variables();
      variables.set('statusCode', statusCode ?? 0);
      variables.set('apimRequestId', apimRequestId || '');
      variables.set('status', 'submitted');

      await taskService.complete(task, variables);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error(`[ExtractRequestId] Error extracting request ID: ${errorMessage}`);
      await taskService.handleFailure(task, errorMessage, 0, 0);
    }
  }
);

console.log('[OCR] Extract Request ID worker started.');




