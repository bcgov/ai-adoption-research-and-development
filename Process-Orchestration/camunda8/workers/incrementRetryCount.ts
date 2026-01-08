import { Camunda8 } from '@camunda8/sdk';
import type { WorkflowVariables, ZeebeJob } from '../src/types';

const camunda = new Camunda8();
const zbc = camunda.getZeebeGrpcApiClient();

/**
 * Worker for incrementing retry count.
 */
zbc.createWorker<WorkflowVariables>({
  taskType: 'increment-retry-count',
  taskHandler: async (job: Readonly<ZeebeJob<WorkflowVariables>>) => {
    const { retryCount } = job.variables;
    
    const currentRetryCount = (retryCount || 0) + 1;
    
    console.log(`[IncrementRetryCount] Previous retry count: ${retryCount || 0}, Incremented retry count to: ${currentRetryCount}`);
    console.log(`[IncrementRetryCount] Will check if ${currentRetryCount} < 20 to continue polling`);
    
    return job.complete({
      retryCount: currentRetryCount
    });
  },
  loglevel: 'INFO'
});

console.log('Increment Retry Count worker started. Waiting for tasks...');

