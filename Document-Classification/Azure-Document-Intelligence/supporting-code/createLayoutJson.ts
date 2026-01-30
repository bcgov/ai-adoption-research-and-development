import { Buffer } from "node:buffer";
import { BlobStorage } from "./blobStorage.ts";
import { UploadConfig } from "./interfaces.ts";
import { DocumentIntelligenceClient } from "@azure-rest/ai-document-intelligence";
import { pollOperation } from "./operationHandler.ts";

const apiKey = Deno.env.get("AZURE_DOCUMENT_INTELLIGENCE_API_KEY")!;

// Each file in a training folder needs accompanying layout json.
// The file must be named just like its corresponding image + .ocr.json
// e.g. If image is file.jpg, layout json must be file.jpg.ocr.json.
export const createLayoutJson = async (blob: BlobStorage, containerName: string, uploadConfigs: UploadConfig[], client: DocumentIntelligenceClient) => {
  const containerClient = blob.getContainerClient(containerName);

  // Looping through each folder of training data
  for (const uc of uploadConfigs) {
    // List blobs with the prefix for this doc type
    const prefix = uc.blobFolder.endsWith('/') ? uc.blobFolder : uc.blobFolder + '/';
    const iter = containerClient.listBlobsFlat({ prefix });

    // Analyze each file
    for await (const blobItem of iter) {
      if (!blobItem.name.match(/\.(jpg|jpeg|png|bmp|tif|tiff)$/i)) continue; // Only process images
      const url = blob.getBlobSasUrl(containerName, blobItem.name);

      // Run general layout model
      const analyzeResponse = await client.path('/documentModels/prebuilt-layout:analyze').post({
        body: {
          urlSource: url,
        },
        queryParameters: { "api-version": "2024-11-30" },
      });

      if (analyzeResponse.status == '202') {
        // Poll operation-location until succeeded or failed
        const operationLocation = analyzeResponse.headers["operation-location"] || analyzeResponse.headers["Operation-Location"];
        if (!operationLocation) {
          console.error("No operation-location header returned for 202 response");
          continue;
        }
        await pollOperation(operationLocation, async (result) => {
          // Save JSON result to blob storage with same base name but .ocr.json extension
          const jsonBlobName = blobItem.name + '.ocr.json';
          const blockBlobClient = containerClient.getBlockBlobClient(jsonBlobName);
          await blockBlobClient.upload(
            Buffer.from(JSON.stringify(result, null, 2)),
            Buffer.byteLength(JSON.stringify(result, null, 2))
          );
          console.log(`Uploaded layout JSON to blob: ${jsonBlobName}`);
        }, (result) => {
          console.error("Analyze operation failed:", result);
        })
      } else if (analyzeResponse.status == '404') {
        // Possible fallback if the url doesn't work. Download and analyze via upload.
        // I haven't had to rely on this so far.
        console.warn(`404 from analyze API for ${blobItem.name}, falling back to download/upload method.`);
        console.warn(`Original error`, analyzeResponse.body)
        console.warn(`Original error`, analyzeResponse.request)
        // Download the blob
        const blobResp = await fetch(url);
        if (!blobResp.ok) {
          console.error(`Failed to download blob for fallback: ${blobItem.name}`);
          continue;
        }
        const fileBuffer = Buffer.from(await blobResp.arrayBuffer());
        // Fallback: Send as base64Source in JSON body
        const uploadResponse = await client.path('/documentModels/{modelId}:analyze').post({
          body: { base64Source: fileBuffer.toString('base64') },
          queryParameters: { "api-version": "2024-11-30" },
          pathParameters: { "modelId": "prebuilt-layout" },
          headers: { 'Content-Type': 'application/json' }
        });
        if (uploadResponse.status == '200') {
          const jsonBlobName = blobItem.name + '.ocr.json';
          const blockBlobClient = containerClient.getBlockBlobClient(jsonBlobName);
          await blockBlobClient.upload(
            Buffer.from(JSON.stringify(uploadResponse.body, null, 2)),
            Buffer.byteLength(JSON.stringify(uploadResponse.body, null, 2))
          );
          console.log(`Uploaded layout JSON to blob (fallback): ${jsonBlobName}`);
        } else {
          console.error(`Fallback analyze failed for ${blobItem.name}:`, uploadResponse.status, uploadResponse.body);
        }
      } else {
        console.error(`Failed to analyze blob ${blobItem.name}:`, analyzeResponse.status, analyzeResponse.body);
      }
    }
  }
}
