/**
 * Temporal Workflow for Azure OCR Document Processing
 * This workflow orchestrates the OCR process with polling and retry logic
 */

import { sleep, proxyActivities } from '@temporalio/workflow';
import type { OCRWorkflowInput, OCRResult, PreparedFileData, SubmissionResult, PollResult } from './types';
import type * as activities from './activities';

// Create activity proxies (required for Temporal workflows)
const {
  prepareFileData,
  submitToAzureOCR,
  pollOCRResults,
  extractOCRResults
} = proxyActivities<typeof activities>({
  startToCloseTimeout: '5 minutes',
  retry: {
    maximumAttempts: 3
  }
});

/**
 * Main OCR Workflow
 * Processes a document through Azure Document Intelligence OCR
 */
export async function ocrWorkflow(input: OCRWorkflowInput): Promise<OCRResult> {
  // Step 1: Prepare file data
  const fileData: PreparedFileData = await prepareFileData(input);

  // Step 2: Submit to Azure OCR (returns submission result with request ID)
  const submissionResult: SubmissionResult = await submitToAzureOCR(fileData);

  // Step 4: Wait 5 seconds before first poll (matching n8n workflow)
  await sleep(5000);

  // Step 5: Poll loop with retry logic
  let retryCount = 0;
  const maxRetries = 20;
  let pollResult: PollResult | null = null;
  let ocrResponse: PollResult['response'] | undefined = undefined;

  while (true) {
    // Poll OCR results
    pollResult = await pollOCRResults(submissionResult.apimRequestId);

    // If status is not "running", break the loop
    if (pollResult.status !== 'running') {
      ocrResponse = pollResult.response;
      break;
    }

    // Status is "running", increment retry count
    retryCount++;

    // Check if max retries exceeded
    if (retryCount >= maxRetries) {
      throw new Error(
        `OCR processing timed out after ${maxRetries} retries. Last status: ${pollResult.status}`
      );
    }

    // Wait 10 seconds before next poll (matching n8n workflow)
    await sleep(10000);
  }

  // Step 6: Extract OCR results
  const result: OCRResult = await extractOCRResults(
    submissionResult.apimRequestId,
    fileData.fileName,
    fileData.fileType,
    ocrResponse
  );

  return result;
}

