import { Camunda8 } from '@camunda8/sdk';
import * as fs from 'fs-extra';
import * as path from 'path';
import type { WorkflowVariables, ZeebeJob } from '../src/types';

const camunda = new Camunda8();
const zbc = camunda.getZeebeGrpcApiClient();

/**
 * Worker for reading files from disk.
 * Equivalent to n8n's "Read File from Disk" node.
 */
zbc.createWorker<WorkflowVariables>({
  taskType: 'read-file-from-disk',
  taskHandler: async (job: Readonly<ZeebeJob<WorkflowVariables>>) => {
    const { filePath } = job.variables;
    const filePathToRead = filePath || '/data/input.pdf';
    
    console.log(`[ReadFileFromDisk] Reading file from disk: ${filePathToRead}`);
    
    try {
      // Read file content
      const fileBuffer = await fs.readFile(filePathToRead);
      
      // Convert to base64 for storage in process variables
      const base64Content = fileBuffer.toString('base64');
      
      // Extract filename from path
      const fileName = path.basename(filePathToRead);
      
      console.log(`[ReadFileFromDisk] Successfully read file: ${fileName} (${fileBuffer.length} bytes)`);
      
      // Complete the job with variables
      return job.complete({
        fileContent: base64Content,
        fileName: fileName
      });
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error(`[ReadFileFromDisk] Error reading file: ${errorMessage}`);
      return job.fail(errorMessage); // This will fail the job
    }
  },
  loglevel: 'INFO'
});

console.log('Read File from Disk worker started. Waiting for tasks...');

