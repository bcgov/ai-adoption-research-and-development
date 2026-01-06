/**
 * Type definitions for Camunda workflow variables and Azure OCR responses
 */

// Workflow Variables
export interface WorkflowVariables {
  // File input variables
  filePath?: string;
  fileContent?: string;
  fileName?: string;
  fileType?: 'pdf' | 'image';
  contentType?: string;
  binaryData?: string; // base64 encoded

  // Webhook variables
  webhookBody?: string | WebhookBody;
  webhookHeaders?: string | Record<string, string>;

  // Azure OCR variables
  httpResponse?: string | HttpResponse;
  statusCode?: number;
  apimRequestId?: string;
  status?: string;

  // OCR polling variables
  retryCount?: number;
  ocrResponse?: string | OCRResponse;
  ocrStatus?: 'running' | 'succeeded' | 'failed';

  // OCR results
  ocrResult?: OCRResult;
}

export interface WebhookBody {
  data?: string;
  file?: string;
  original_filename?: string;
  filename?: string;
  file_type?: string;
  content_type?: string;
}

export interface HttpResponse {
  statusCode: number;
  headers: Record<string, string | string[]>;
  apimRequestId?: string;
}

export interface OCRResponse {
  status: 'running' | 'succeeded' | 'failed';
  analyzeResult?: AnalyzeResult;
  createdDateTime?: string;
  lastUpdatedDateTime?: string;
  error?: {
    code: string;
    message: string;
  };
}

export interface AnalyzeResult {
  apiVersion: string;
  modelId: string;
  content: string;
  pages: Page[];
  paragraphs: Paragraph[];
  tables: Table[];
  keyValuePairs: KeyValuePair[];
  sections: Section[];
  figures: Figure[];
}

export interface Page {
  pageNumber: number;
  width: number;
  height: number;
  unit: string;
  words: Word[];
  lines: Line[];
  spans: Span[];
}

export interface Word {
  content: string;
  polygon: number[];
  confidence: number;
  span: Span;
}

export interface Line {
  content: string;
  polygon: number[];
  spans: Span[];
}

export interface Span {
  offset: number;
  length: number;
}

export interface Paragraph {
  role?: string;
  content: string;
  boundingRegions: BoundingRegion[];
  spans: Span[];
}

export interface BoundingRegion {
  pageNumber: number;
  polygon: number[];
}

export interface Table {
  rowCount: number;
  columnCount: number;
  cells: TableCell[];
  boundingRegions: BoundingRegion[];
  spans: Span[];
}

export interface TableCell {
  kind?: 'content' | 'rowHeader' | 'columnHeader' | 'stubHead' | 'description';
  rowIndex: number;
  columnIndex: number;
  rowSpan?: number;
  columnSpan?: number;
  content: string;
  boundingRegions: BoundingRegion[];
  spans: Span[];
}

export interface KeyValuePair {
  key: {
    content: string;
    boundingRegions: BoundingRegion[];
    spans: Span[];
  };
  value?: {
    content: string;
    boundingRegions: BoundingRegion[];
    spans: Span[];
  };
  confidence: number;
}

export interface Section {
  role?: string;
  content: string;
  boundingRegions: BoundingRegion[];
  spans: Span[];
}

export interface Figure {
  content: string;
  boundingRegions: BoundingRegion[];
  spans: Span[];
}

export interface OCRResult {
  extractedText: string;
  pages: Page[];
  tables: Table[];
  paragraphs: Paragraph[];
  keyValuePairs: KeyValuePair[];
  sections: Section[];
  figures: Figure[];
  status: string;
  apimRequestId: string;
  fileName: string;
  fileType: string;
  processedAt: string;
}

export interface ExternalTaskHandlerArgs {
  task: {
    id?: string;
    variables: {
      getAll<T = WorkflowVariables>(): T;
      get<T = unknown>(name: string): T;
    };
  };
  taskService: {
    complete: (task: unknown, variables?: unknown) => Promise<void>;
    handleFailure: (
      task: unknown,
      errorMessage: string,
      retries: number,
      retryTimeout: number
    ) => Promise<void>;
  };
}

export interface JobHandlerResult {
  [key: string]: unknown;
}

