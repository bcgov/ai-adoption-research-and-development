/**
 * Temporal Activities for OCR Workflow
 * Activities handle non-deterministic operations (HTTP calls, file processing)
 */

// Load environment variables first (before reading them)
require('dotenv').config();

import axios, { AxiosResponse } from 'axios';
import type {
  PreparedFileData,
  SubmissionResult,
  PollResult,
  OCRResponse,
  OCRResult,
  OCRWorkflowInput
} from './types';

const endpoint = process.env.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT;
const apiKey = process.env.AZURE_DOCUMENT_INTELLIGENCE_API_KEY;

/**
 * Normalize endpoint URL by removing trailing slash
 */
function normalizeEndpoint(url: string | undefined): string {
  if (!url) return '';
  return url.endsWith('/') ? url.slice(0, -1) : url;
}

/**
 * Activity: Prepare file data for Azure OCR
 * Validates binary data and extracts metadata
 */
export async function prepareFileData(input: OCRWorkflowInput): Promise<PreparedFileData> {
  console.log('[PrepareFileData] ===== DEBUG START =====');
  console.log('[PrepareFileData] Preparing file data for Azure OCR');
  console.log(`[PrepareFileData] Input keys:`, Object.keys(input));
  console.log(`[PrepareFileData] File name: ${input.fileName || 'not provided'}`);
  console.log(`[PrepareFileData] File type: ${input.fileType || 'not provided'}`);
  console.log(`[PrepareFileData] Content type: ${input.contentType || 'not provided'}`);
  console.log(`[PrepareFileData] Binary data length: ${input.binaryData?.length || 0} bytes (base64)`);

  let fileName = input.fileName || 'document';
  let fileType: 'pdf' | 'image' = input.fileType || 'pdf';
  let contentType = input.contentType || 'application/pdf';
  const binaryData = input.binaryData;

  if (!binaryData || typeof binaryData !== 'string') {
    throw new Error('No binary data provided. Binary data must be a base64-encoded string.');
  }

  // Validate base64 format
  try {
    Buffer.from(binaryData, 'base64');
  } catch (error) {
    throw new Error('Invalid base64-encoded binary data');
  }

  // Determine file type from filename or content type
  const lowerFileName = fileName.toLowerCase();
  if (contentType.includes('pdf') || lowerFileName.endsWith('.pdf')) {
    fileType = 'pdf';
    contentType = 'application/pdf';
  } else if (
    contentType.includes('image') ||
    lowerFileName.match(/\.(jpg|jpeg|png|gif|bmp|tiff|webp)$/i)
  ) {
    fileType = 'image';
    if (!contentType || contentType === 'application/pdf') {
      if (lowerFileName.endsWith('.png')) {
        contentType = 'image/png';
      } else if (lowerFileName.match(/\.(jpg|jpeg)$/i)) {
        contentType = 'image/jpeg';
      } else if (lowerFileName.endsWith('.gif')) {
        contentType = 'image/gif';
      } else {
        contentType = contentType || 'image/jpeg';
      }
    }
  }

  // Validate PDF signature if it's supposed to be a PDF
  if (fileType === 'pdf' || contentType.includes('pdf')) {
    try {
      const buffer = Buffer.from(binaryData, 'base64');
      const pdfSignature = buffer.slice(0, 4).toString();
      if (pdfSignature !== '%PDF' && buffer.length > 4) {
        console.warn('[PrepareFileData] WARNING: File does not have valid PDF signature!');
      }
    } catch (e) {
      console.warn('[PrepareFileData] Could not validate PDF signature:', e);
    }
  }

  console.log(
    `[PrepareFileData] Prepared file: ${fileName}, type: ${fileType}, contentType: ${contentType}`
  );
  console.log(`[PrepareFileData] Binary data length (final): ${binaryData.length} bytes (base64)`);
  console.log(`[PrepareFileData] ===== DEBUG END =====`);

  return {
    fileName,
    fileType,
    contentType,
    binaryData
  };
}

/**
 * Activity: Submit document to Azure Document Intelligence OCR API
 * Returns serializable response data with headers including apim-request-id
 */
export async function submitToAzureOCR(
  fileData: PreparedFileData
): Promise<SubmissionResult> {
  console.log('[SubmitToAzureOCR] ===== DEBUG START =====');
  console.log(`[SubmitToAzureOCR] Endpoint (raw): ${endpoint}`);
  console.log(`[SubmitToAzureOCR] API Key present: ${!!apiKey}`);

  if (!endpoint || !apiKey) {
    console.error('[SubmitToAzureOCR] Missing credentials!');
    throw new Error(
      'Azure Document Intelligence credentials not configured. Set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and AZURE_DOCUMENT_INTELLIGENCE_API_KEY environment variables.'
    );
  }

  const normalizedEndpoint = normalizeEndpoint(endpoint);
  const url = `${normalizedEndpoint}/documentModels/prebuilt-layout:analyze?api-version=2024-11-30&features=keyValuePairs`;

  console.log(`[SubmitToAzureOCR] Normalized endpoint: ${normalizedEndpoint}`);
  console.log(`[SubmitToAzureOCR] Full URL: ${url}`);
  console.log(`[SubmitToAzureOCR] Content-Type: ${fileData.contentType}`);
  console.log(`[SubmitToAzureOCR] Data size (base64): ${fileData.binaryData.length} bytes`);

  try {
    const fileBuffer = Buffer.from(fileData.binaryData, 'base64');
    console.log(`[SubmitToAzureOCR] File buffer size (decoded): ${fileBuffer.length} bytes`);
    console.log(`[SubmitToAzureOCR] File buffer first 20 bytes (hex): ${fileBuffer.slice(0, 20).toString('hex')}`);

    const requestHeaders = {
      'api-key': apiKey ? `${apiKey.substring(0, 4)}...${apiKey.substring(apiKey.length - 4)}` : 'MISSING',
      'Content-Type': fileData.contentType
    };
    console.log(`[SubmitToAzureOCR] Request headers:`, {
      'api-key': requestHeaders['api-key'],
      'Content-Type': requestHeaders['Content-Type']
    });

    console.log(`[SubmitToAzureOCR] Making POST request to: ${url}`);
    const response: AxiosResponse = await axios.post(url, fileBuffer, {
      headers: {
        'api-key': apiKey,
        'Content-Type': fileData.contentType
      },
      maxContentLength: Infinity,
      maxBodyLength: Infinity
    });
    
    console.log(`[SubmitToAzureOCR] Response status: ${response.status}`);
    console.log(`[SubmitToAzureOCR] Response headers:`, JSON.stringify(response.headers, null, 2));

    const statusCode = response.status;
    const apimRequestId =
      response.headers['apim-request-id'] ||
      response.headers['Apim-Request-Id'] ||
      response.headers['APIM-Request-Id'] ||
      null;

    console.log(
      `[SubmitToAzureOCR] Azure OCR submission response: Status=${statusCode}, APIM-Request-ID=${apimRequestId}`
    );

    // Validate status code
    if (statusCode !== 202) {
      console.error(`[SubmitToAzureOCR] Unexpected status code: ${statusCode} (expected 202)`);
      console.error(`[SubmitToAzureOCR] Response data:`, response.data);
      throw new Error(
        `Failed to submit document to Azure OCR. Expected status code 202, got ${statusCode}`
      );
    }

    if (!apimRequestId) {
      console.error(`[SubmitToAzureOCR] APIM Request ID not found in headers`);
      console.error(`[SubmitToAzureOCR] Available headers:`, Object.keys(response.headers));
      throw new Error('APIM Request ID not found in response headers');
    }

    console.log(`[SubmitToAzureOCR] ===== DEBUG END (SUCCESS) =====`);
    
    // Return serializable result
    return {
      statusCode,
      apimRequestId: apimRequestId as string,
      headers: response.headers as Record<string, string | string[]>
    };
  } catch (error) {
    console.error(`[SubmitToAzureOCR] ===== DEBUG END (ERROR) =====`);
    if (axios.isAxiosError(error)) {
      console.error(`[SubmitToAzureOCR] Axios Error Details:`);
      console.error(`  - Status: ${error.response?.status}`);
      console.error(`  - Status Text: ${error.response?.statusText}`);
      console.error(`  - URL: ${error.config?.url}`);
      console.error(`  - Method: ${error.config?.method}`);
      console.error(`  - Request Headers:`, error.config?.headers);
      console.error(`  - Response Headers:`, error.response?.headers);
      console.error(`  - Response Data:`, error.response?.data);
      console.error(`  - Error Message: ${error.message}`);
    } else {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error(`[SubmitToAzureOCR] Error: ${errorMessage}`);
      if (error instanceof Error && error.stack) {
        console.error(`[SubmitToAzureOCR] Stack:`, error.stack);
      }
    }
    throw error;
  }
}

/**
 * Activity: Poll Azure Document Intelligence for OCR results
 * Returns status and full response if available
 */
export async function pollOCRResults(apimRequestId: string): Promise<PollResult> {
  console.log(`[PollOCRResults] ===== DEBUG START =====`);
  console.log(`[PollOCRResults] APIM Request ID: ${apimRequestId}`);
  console.log(`[PollOCRResults] Endpoint (raw): ${endpoint}`);
  console.log(`[PollOCRResults] API Key present: ${!!apiKey}`);
  
  if (!endpoint || !apiKey) {
    console.error('[PollOCRResults] Missing credentials!');
    throw new Error(
      'Azure Document Intelligence credentials not configured. Set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and AZURE_DOCUMENT_INTELLIGENCE_API_KEY environment variables.'
    );
  }

  if (!apimRequestId || typeof apimRequestId !== 'string') {
    console.error(`[PollOCRResults] Invalid APIM Request ID: ${apimRequestId}`);
    throw new Error('APIM Request ID not available for polling');
  }

  const normalizedEndpoint = normalizeEndpoint(endpoint);
  const url = `${normalizedEndpoint}/documentModels/prebuilt-layout/analyzeResults/${apimRequestId}?api-version=2024-11-30`;

  console.log(`[PollOCRResults] Normalized endpoint: ${normalizedEndpoint}`);
  console.log(`[PollOCRResults] Full URL: ${url}`);

  try {
    console.log(`[PollOCRResults] Making GET request to: ${url}`);
    const response = await axios.get<OCRResponse>(url, {
      headers: {
        'api-key': apiKey
      }
    });

    console.log(`[PollOCRResults] Response status: ${response.status}`);
    console.log(`[PollOCRResults] Response headers:`, JSON.stringify(response.headers, null, 2));

    const responseBody = response.data;

    if (!responseBody) {
      console.error(`[PollOCRResults] Empty response body`);
      throw new Error('Empty response from Azure OCR polling endpoint');
    }

    const status = responseBody.status || 'unknown';
    console.log(`[PollOCRResults] OCR polling response: Status=${status}`);
    console.log(`[PollOCRResults] Response data keys:`, Object.keys(responseBody));
    console.log(`[PollOCRResults] ===== DEBUG END (SUCCESS) =====`);

    return {
      status: status as 'running' | 'succeeded' | 'failed',
      response: responseBody
    };
  } catch (error) {
    console.error(`[PollOCRResults] ===== DEBUG END (ERROR) =====`);
    if (axios.isAxiosError(error)) {
      console.error(`[PollOCRResults] Axios Error Details:`);
      console.error(`  - Status: ${error.response?.status}`);
      console.error(`  - Status Text: ${error.response?.statusText}`);
      console.error(`  - URL: ${error.config?.url}`);
      console.error(`  - Response Headers:`, error.response?.headers);
      console.error(`  - Response Data:`, error.response?.data);
      console.error(`  - Error Message: ${error.message}`);
    } else {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error(`[PollOCRResults] Error: ${errorMessage}`);
      if (error instanceof Error && error.stack) {
        console.error(`[PollOCRResults] Stack:`, error.stack);
      }
    }
    throw error;
  }
}

/**
 * Activity: Extract OCR results from Azure response
 * Parses and structures the OCR data
 */
export async function extractOCRResults(
  apimRequestId: string,
  fileName: string,
  fileType: string,
  ocrResponse?: OCRResponse
): Promise<OCRResult> {
  console.log('[ExtractOCRResults] Extracting OCR results');

  try {
    let ocrResponseObj: OCRResponse | undefined = ocrResponse;

    // If response not provided, fetch it
    if (!ocrResponseObj) {
      if (!endpoint || !apiKey) {
        throw new Error(
          'Azure Document Intelligence credentials not configured. Set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and AZURE_DOCUMENT_INTELLIGENCE_API_KEY environment variables.'
        );
      }
      const normalizedEndpoint = normalizeEndpoint(endpoint);
      const url = `${normalizedEndpoint}/documentModels/prebuilt-layout/analyzeResults/${apimRequestId}?api-version=2024-11-30`;
      console.log(`[ExtractOCRResults] Fetching final OCR result: ${url}`);
      const response = await axios.get<OCRResponse>(url, {
        headers: { 'api-key': apiKey }
      });
      ocrResponseObj = response.data;
    }

    if (!ocrResponseObj) {
      throw new Error('No OCR response available to extract results.');
    }

    const analyzeResult = ocrResponseObj.analyzeResult || {
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
      success: ocrResponseObj.status === 'succeeded',
      status: ocrResponseObj.status || 'unknown',
      apimRequestId: apimRequestId || '',
      fileName: fileName || 'document',
      fileType: fileType || 'pdf',
      extractedText: analyzeResult.content || '',
      pages: analyzeResult.pages || [],
      tables: analyzeResult.tables || [],
      paragraphs: analyzeResult.paragraphs || [],
      keyValuePairs: analyzeResult.keyValuePairs || [],
      sections: analyzeResult.sections || [],
      figures: analyzeResult.figures || [],
      processedAt: new Date().toISOString()
    };

    console.log(
      `[ExtractOCRResults] Extracted results: status=${result.status}, pages=${result.pages.length}, tables=${result.tables.length}`
    );

    return result;
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    console.error(`[ExtractOCRResults] Error extracting OCR results: ${errorMessage}`);
    throw error;
  }
}

