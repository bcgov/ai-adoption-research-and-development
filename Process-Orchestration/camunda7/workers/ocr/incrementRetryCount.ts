import { Variables } from 'camunda-external-task-client-js';
import type { ExternalTaskHandlerArgs, WorkflowVariables } from '../../src/types';
import client from '../client';

/**
 * Worker for incrementing retry count.
 */
client.subscribe(
  'increment-retry-count',
  async ({ task, taskService }: ExternalTaskHandlerArgs) => {
    const { retryCount } = task.variables.getAll<WorkflowVariables>();

    const currentRetryCount = (retryCount || 0) + 1;

    console.log(
      `[IncrementRetryCount] Previous retry count: ${retryCount || 0}, Incremented retry count to: ${currentRetryCount}`
    );
    console.log(`[IncrementRetryCount] Will check if ${currentRetryCount} < 20 to continue polling`);

    const variables = new Variables();
    variables.set('retryCount', currentRetryCount);

    await taskService.complete(task, variables);
  }
);

console.log('[OCR] Increment Retry Count worker started.');




