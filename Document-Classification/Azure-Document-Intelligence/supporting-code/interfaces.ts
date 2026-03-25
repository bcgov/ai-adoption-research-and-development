export interface UploadConfig {
  label: string;
  fromFolder: string;
  blobFolder: string;
}

export interface ClassificationResult {
  status: string;
  createdDateTime: string;
  lastUpdatedDateTime: string;
  analyzeResult: {
    apiVersion: string;
    modelId: string;
    stringIndexType: string;
    content: string;
    pages: Array<{
      pageNumber: number;
      angle: number;
      width: number;
      height: number;
      unit: string;
      words: any[];
      lines: any[];
      spans: any[];
    }>;
    documents: Array<{
      docType: string;
      boundingRegions: any[];
      confidence: number;
      spans: any[];
    }>;
    contentFormat: string;
  };
}
