import { Variables } from 'camunda-external-task-client-js';
import * as fs from 'fs-extra';
import * as path from 'path';
import type { ExternalTaskHandlerArgs, WorkflowVariables } from '../../src/types';
import client from '../client';

/**
 * Worker for reading files from disk.
 * Equivalent to n8n's "Read File from Disk" node.
 */
client.subscribe(
  'read-file-from-disk',
  async ({ task, taskService }: ExternalTaskHandlerArgs) => {
    const { filePath } = task.variables.getAll<WorkflowVariables>();
    const filePathToRead = filePath || '/data/input.pdf';

    console.log(`[ReadFileFromDisk] Reading file from disk: ${filePathToRead}`);

    try {
      const fileBuffer = await fs.readFile(filePathToRead);
      const base64Content = fileBuffer.toString('base64');
      const fileName = path.basename(filePathToRead);

      console.log(
        `[ReadFileFromDisk] Successfully read file: ${fileName} (${fileBuffer.length} bytes)`
      );

      const variables = new Variables();
      variables.set('fileContent', base64Content);
      variables.set('fileName', fileName);

      await taskService.complete(task, variables);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error(`[ReadFileFromDisk] Error reading file: ${errorMessage}`);
      await taskService.handleFailure(task, errorMessage, 0, 0);
    }
  }
);

console.log('[OCR] Read File from Disk worker started.');




