import DocumentIntelligence from '@azure-rest/ai-document-intelligence';
import { BlobStorage } from "./blob-storage.ts";
import { Buffer } from "node:buffer";

const trainEndpoint = Deno.env.get("AZURE_DOCUMENT_INTELLIGENCE_TRAIN_ENDPOINT")!;
const apiKey = Deno.env.get("AZURE_DOCUMENT_INTELLIGENCE_API_KEY")!;

// Create blob storage, upload documents
const blob = new BlobStorage();
const containerName = 'classifier';
const trainingClient = DocumentIntelligence(trainEndpoint, { key: apiKey }, {
  credentials: {
    apiKeyHeaderName: "api-key",
  }
});


const uploadDocuments = async (fromFolder: string, blobFolder: string = 'documents', max: number = 10) => {
  const fileNames: string[] = [];
  for await (const entry of Deno.readDir(fromFolder)) {
    if (entry.isFile) {
      fileNames.push(entry.name);
    }
  }

  // Limit to max files
  const limitedFileNames = fileNames.slice(0, max);

  const files = await Promise.all(
    limitedFileNames.map(async (name) => {
      const filePath = `${fromFolder}/${name}`;
      const fileData = await Deno.readFile(filePath);
      return { name, content: fileData.buffer as unknown as Buffer };
    })
  );

  const uploadResult = await blob.uploadFiles(containerName, files.map(f => ({ name: `${blobFolder}/${f.name}`, content: f.content })));
  return uploadResult;
};

interface UploadConfig {
  label: string;
  fromFolder: string;
  blobFolder: string;
}
const uploadConfigs: UploadConfig[] = [
  { label: 'monthly-report', fromFolder: './report_documents', blobFolder: 'monthly-reports' },
  { label: 'other', fromFolder: './other_documents', blobFolder: 'other' }
]

// for (const uc of uploadConfigs){
//   await uploadDocuments(uc.fromFolder, uc.blobFolder);
// }

// Produce layout files for these folders (from blob storage, use urlSource, save JSON to blob storage)
const containerClient = blob.getContainerClient(containerName);
const createLayoutJson = async () => {
  for (const uc of uploadConfigs) {
    // List blobs with the prefix for this doc type
    const prefix = uc.blobFolder.endsWith('/') ? uc.blobFolder : uc.blobFolder + '/';
    const iter = containerClient.listBlobsFlat({ prefix });
    console.log(iter)
    for await (const blobItem of iter) {
      if (!blobItem.name.match(/\.(jpg|jpeg|png|bmp|tif|tiff)$/i)) continue; // Only process images
      const url = blob.getBlobSasUrl(containerName, blobItem.name);
      console.log('Generated SAS URL:', url);
      // Debug: Try to fetch the blob to verify accessibility
      try {
        const testResp = await fetch(url);
        if (!testResp.ok) {
          console.error(`Blob SAS URL fetch failed for ${blobItem.name}:`, testResp.status, testResp.statusText);
          continue;
        } else {
          console.log(`Blob SAS URL fetch succeeded for ${blobItem.name}`);
          // console.log(await testResp.headers)
        }
      } catch (err) {
        console.error(`Blob SAS URL fetch error for ${blobItem.name}:`, err);
        continue;
      }
      // Run general layout model
      const analyzeResponse = await trainingClient.path('/documentModels/prebuilt-layout:analyze').post({
        body: {
          urlSource: url,
        },
        queryParameters: { "api-version": "2024-11-30" },
        // pathParameters: {"modelId": "prebuilt-layout"},
      });
      // TODO: Do we need to worry about these other fallbacks?
      if (analyzeResponse.status == 202) {
        // Poll operation-location until succeeded or failed
        let operationLocation = analyzeResponse.headers["operation-location"] || analyzeResponse.headers["Operation-Location"];
        if (!operationLocation) {
          console.error("No operation-location header returned for 202 response");
          continue;
        }
        let status = "notStarted";
        let result;
        while (status !== "succeeded" && status !== "failed") {
          await new Promise((res) => setTimeout(res, 5000)); // wait 5 seconds
          const pollResp = await fetch(operationLocation, {
            headers: { "api-key": apiKey },
          });
          result = await pollResp.json();
          status = result.status || result.analyzeResult?.status || result.modelInfo?.status;
          console.log(`Analyze operation status: ${status}`);
        }
        if (status === "succeeded") {
          // Save JSON result to blob storage with same base name but .json extension
          const jsonBlobName = blobItem.name + '.ocr.json';
          const blockBlobClient = containerClient.getBlockBlobClient(jsonBlobName);
          await blockBlobClient.upload(
            Buffer.from(JSON.stringify(result, null, 2)),
            Buffer.byteLength(JSON.stringify(result, null, 2))
          );
          console.log(`Uploaded layout JSON to blob: ${jsonBlobName}`);
        } else {
          console.error("Analyze operation failed:", result);
        }
      } else if (analyzeResponse.status == 404) {
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
        const uploadResponse = await trainingClient.path('/documentModels/{modelId}:analyze').post({
          body: { base64Source: fileBuffer.toString('base64') },
          queryParameters: { "api-version": "2024-11-30" },
          pathParameters: { "modelId": "prebuilt-layout" },
          headers: { 'Content-Type': 'application/json' }
        });
        if (uploadResponse.status == 200) {
          // const jsonBlobName = blobItem.name.replace(/\.[^.]+$/, '.json');

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

// await createLayoutJson();

const generateTrainingConfig = (classifierId: string, description: string, uploadConfigs: UploadConfig[], containerUrl: string) => {
  const docTypes: Record<string, any> = {};
  for (const uc of uploadConfigs) {
    const docType = uc.label;
    docTypes[docType] = {
      azureBlobSource: {
        containerUrl,
        prefix: uc.blobFolder.endsWith('/') ? uc.blobFolder : uc.blobFolder + '/'
      }
    };
  }
  // NOTE: baseClassifierId cannot be the same one you are overwriting.
  // It will not find the original. Possibly clears beforehand.
  return {
    classifierId,
    description,
    docTypes,
    allowOverwrite: true, // Default is false,
    // baseClassifierId: classifierId
  };
};
const classifierName = 'monthly-report-classifier';

const trainModel = async () => {
  // Example usage after uploads:
  const containerUrl = await blob.generateSasUrl(containerName);
  const trainingConfig = generateTrainingConfig(
    classifierName,
    'classifies documents as monthly reports or not',
    uploadConfigs,
    containerUrl
  );
  console.log(JSON.stringify(trainingConfig, null, 2));

  // Run training of classifier
  const response = await trainingClient.path('/documentClassifiers:build',).post({
    body: trainingConfig,
    queryParameters: { "api-version": "2024-11-30" },
  });


  // Poll operation status if 202 Accepted
  let operationLocation = response.headers["operation-location"] || response.headers["Operation-Location"];
  if (response.status == '202' && operationLocation) {
    // Returned operation-location header uses wrong domain:
    // Replace for this:
    // ai-services-hub-test-apim.azure-api.net/sdpr-invoice-automation
    operationLocation = operationLocation.replace(
      /https:\/\/[^/]+\/documentintelligence/,
      'https://ai-services-hub-test-apim.azure-api.net/sdpr-invoice-automation/documentintelligence'
    );
    let status = "notStarted";
    let result;
    while (status !== "succeeded" && status !== "failed") {
      await new Promise((res) => setTimeout(res, 5000)); // wait 5 seconds
      const pollResp = await fetch(operationLocation, {
        headers: { "api-key": apiKey },
      });
      result = await pollResp.json();
      status = result.status || result.modelInfo?.status;
      console.log(`Training status: ${status}`);
    }
    if (status === "failed") {
      console.error("Training failed:", result);
      // throw new Error("Classifier training failed");
    }
  } else {
    console.log(response.status);
    console.log(response.body);
    // console.log(response.headers);
    // console.log(response.request)
  }
  const classifier = await trainingClient.path(`/documentClassifiers/${classifierName}`).get({
    queryParameters: { "api-version": "2024-11-30" },
  })
  console.log(classifier.status)
  console.log(classifier.body)
}
// await trainModel();
// await blob.deleteContainerIfExists(containerName);

const classifyDocument = async (filePath: string) => {
  // Read file and encode to base64
  const fileData = await Deno.readFile(filePath);
  const base64String = Buffer.from(fileData).toString('base64');

  const response = await trainingClient.path(`/documentClassifiers/${classifierName}:analyze`).post({
    body: {
      base64Source: base64String
    },
    queryParameters: { "api-version": "2024-11-30", "_overload": "classifyDocument" },
  });
  console.log(response.headers['operation-location'])
  console.log(response.status)
  if (response.status == 202) {
    const operationLocation = response.headers["operation-location"] || response.headers["Operation-Location"];
    return { status: 202, content: response.headers['operation-location'] };
  }
  return { status: response.status, content: response.body };
}

interface ClassificationResult {
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

// Poll operation-location for result
const pollClassificationResult = async (operationLocation: string): Promise<ClassificationResult> => {
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

const testDocuments = [
  './report_documents/form_image_44.jpg',
  './report_documents/form_image_77.jpg',
  './other_documents/01122115.png',
  './other_documents/0001463282.png'
]

for (const d of testDocuments) {
  const { status, content } = await classifyDocument(d);
  console.log(status, content)
  if (status == 202) {
    const result = await pollClassificationResult(content)
    console.log(result)
  }
}






