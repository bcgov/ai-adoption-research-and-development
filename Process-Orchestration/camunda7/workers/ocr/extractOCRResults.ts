import { Variables } from 'camunda-external-task-client-js';
import axios from 'axios';
import type {
  AnalyzeResult,
  ExternalTaskHandlerArgs,
  OCRResponse,
  OCRResult,
  WorkflowVariables
} from '../../src/types';
import client from '../client';

/**
 * Worker for extracting OCR results from Azure response.
 */
client.subscribe(
  'extract-ocr-results',
  async ({ task, taskService }: ExternalTaskHandlerArgs) => {
    const { ocrResponse, apimRequestId, fileName, fileType } =
      task.variables.getAll<WorkflowVariables>();

    console.log('[ExtractOCRResults] Extracting OCR results');

    try {
      let ocrResponseObj: OCRResponse | undefined;

      if (ocrResponse) {
        ocrResponseObj =
          typeof ocrResponse === 'string'
            ? (JSON.parse(ocrResponse) as OCRResponse)
            : (ocrResponse as OCRResponse);
      } else if (apimRequestId) {
        const endpoint = process.env.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT;
        const apiKey = process.env.AZURE_DOCUMENT_INTELLIGENCE_API_KEY;
        if (!endpoint || !apiKey) {
          throw new Error(
            'Azure Document Intelligence credentials not configured. Set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and AZURE_DOCUMENT_INTELLIGENCE_API_KEY environment variables.'
          );
        }
        const url = `${endpoint}/documentModels/prebuilt-layout/analyzeResults/${apimRequestId}?api-version=2024-11-30`;
        console.log(`[ExtractOCRResults] Fetching final OCR result: ${url}`);
        const response = await axios.get<OCRResponse>(url, {
          headers: { 'api-key': apiKey }
        });
        ocrResponseObj = response.data;
      }

      if (!ocrResponseObj) {
        throw new Error('No OCR response available to extract results.');
      }

      const analyzeResult: AnalyzeResult = ocrResponseObj?.analyzeResult || {
        apiVersion: '',
        modelId: '',
        content: '',
        pages: [],
        paragraphs: [],
        tables: [],
        keyValuePairs: [],
        sections: [],
        figures: []
      };

      const result: OCRResult = {
        extractedText: analyzeResult.content || '',
        pages: analyzeResult.pages || [],
        tables: analyzeResult.tables || [],
        paragraphs: analyzeResult.paragraphs || [],
        keyValuePairs: analyzeResult.keyValuePairs || [],
        sections: analyzeResult.sections || [],
        figures: analyzeResult.figures || [],
        status: ocrResponseObj.status || 'completed',
        apimRequestId: apimRequestId || '',
        fileName: fileName || 'document',
        fileType: fileType || 'pdf',
        processedAt: new Date().toISOString()
      };

      console.log(
        `[ExtractOCRResults] Extracted results: status=${result.status}, pages=${result.pages.length}, tables=${result.tables.length}`
      );
      console.log(
        `[ExtractOCRResults] OCR Response status: ${ocrResponseObj.status}, OCRResult status: ${result.status}`
      );

      const variables = new Variables();
      const ocrStatusFinal = ocrResponseObj.status || result.status;
      variables.set('ocrStatus', ocrStatusFinal);

      const summary = {
        status: ocrStatusFinal,
        apimRequestId: apimRequestId || '',
        fileName: fileName || 'document',
        fileType: fileType || 'pdf',
        pageCount: result.pages.length,
        contentLength: result.extractedText?.length || 0,
        processedAt: result.processedAt
      };
      variables.set('ocrSummary', summary);

      // Small preview text only (avoid large payloads)
      const preview = (result.extractedText || '').slice(0, 2000);
      variables.set('ocrPreviewText', preview);

      const reviewBase = process.env.HITL_REVIEW_BASE_URL || 'https://example.com/review';
      const reviewUrl = `${reviewBase}/${apimRequestId || fileName || 'document'}`;
      variables.set('reviewUrl', reviewUrl);

      await taskService.complete(task, variables);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error(`[ExtractOCRResults] Error extracting OCR results: ${errorMessage}`);
      await taskService.handleFailure(task, errorMessage, 0, 0);
    }
  }
);

console.log('[OCR] Extract OCR Results worker started.');




