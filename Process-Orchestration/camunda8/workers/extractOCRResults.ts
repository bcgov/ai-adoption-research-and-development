import { Camunda8 } from '@camunda8/sdk';
import type { WorkflowVariables, OCRResponse, OCRResult, AnalyzeResult, ZeebeJob } from '../src/types';

const camunda = new Camunda8();
const zbc = camunda.getZeebeGrpcApiClient();

/**
 * Worker for extracting OCR results from Azure response.
 */
zbc.createWorker<WorkflowVariables>({
  taskType: 'extract-ocr-results',
  taskHandler: async (job: Readonly<ZeebeJob<WorkflowVariables>>) => {
    const { ocrResponse, apimRequestId, fileName, fileType } = job.variables;
    
    console.log('[ExtractOCRResults] Extracting OCR results');
    
    try {
      // Parse OCR response
      const ocrResponseObj: OCRResponse = typeof ocrResponse === 'string' 
        ? JSON.parse(ocrResponse) as OCRResponse
        : ocrResponse as OCRResponse;
      
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
      
      console.log(`[ExtractOCRResults] Extracted results: status=${result.status}, pages=${result.pages.length}, tables=${result.tables.length}`);
      console.log(`[ExtractOCRResults] OCR Response status: ${ocrResponseObj.status}, OCRResult status: ${result.status}`);
      
      // Cast to any to satisfy strict JSON type - the object is serializable
      return job.complete({
        ocrResult: result,
        // Also preserve the ocrStatus from polling for the gateway condition
        ocrStatus: ocrResponseObj.status || result.status
      } as any);
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error(`[ExtractOCRResults] Error extracting OCR results: ${errorMessage}`);
      return job.fail(errorMessage);
    }
  },
  loglevel: 'INFO'
});

console.log('Extract OCR Results worker started. Waiting for tasks...');

