import { Buffer } from "node:buffer";
import { ClassificationResult } from "./interfaces.ts";
import { DocumentIntelligenceClient } from "@azure-rest/ai-document-intelligence";

const apiKey = Deno.env.get("AZURE_DOCUMENT_INTELLIGENCE_API_KEY")!;

export const requestClassification = async (client: DocumentIntelligenceClient, classifierName: string, filePath: string) => {
  // Read file and encode to base64
  const fileData = await Deno.readFile(filePath);
  const base64String = Buffer.from(fileData).toString('base64');

  const response = await client.path(`/documentClassifiers/${classifierName}:analyze`).post({
    body: {
      base64Source: base64String
    },
    queryParameters: { "api-version": "2024-11-30", "_overload": "classifyDocument" },
  });
  if (response.status == '202') {
    const operationLocation = response.headers["operation-location"] || response.headers["Operation-Location"];
    return { status: 202, content: operationLocation };
  }
  return { status: response.status, content: '', error: response.body };
}


// Poll operation-location for result
export const pollClassificationResult = async (operationLocation: string): Promise<ClassificationResult> => {
  let status = "notStarted";
  let result;
  while (status !== "succeeded" && status !== "failed") {
    await new Promise((res) => setTimeout(res, 5000)); // wait 5 seconds
    const pollResp = await fetch(operationLocation, {
      headers: { "api-key": apiKey },
    });
    result = await pollResp.json();
    status = result.status || result.analyzeResult?.status || result.modelInfo?.status;
    console.log(`Classification operation status: ${status}`);
  }
  return result;
}
