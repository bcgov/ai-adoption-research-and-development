import DocumentIntelligence from '@azure-rest/ai-document-intelligence';
import { BlobStorage } from "./supporting-code/blobStorage.ts";
import { requestClassification } from "./supporting-code/classification.ts";
import { UploadConfig } from "./supporting-code/interfaces.ts";
import { createLayoutJson } from "./supporting-code/createLayoutJson.ts";
import { uploadDocuments } from "./supporting-code/uploadDocuments.ts";
import { trainClassifier } from "./supporting-code/trainClassifier.ts";
import { pollOperation } from "./supporting-code/operationHandler.ts";

const trainEndpoint = Deno.env.get("AZURE_DOCUMENT_INTELLIGENCE_TRAIN_ENDPOINT")!;
const apiKey = Deno.env.get("AZURE_DOCUMENT_INTELLIGENCE_API_KEY")!;

// Create blob storage, define client
const blob = new BlobStorage();
const containerName = 'classifier';
const trainingClient = DocumentIntelligence(trainEndpoint, { key: apiKey }, {
  credentials: {
    apiKeyHeaderName: "api-key",
  }
});

// This config informs upload, layout generation, and training instructions.
const uploadConfigs: UploadConfig[] = JSON.parse(
  await Deno.readTextFile('./uploadConfigs.json')
);

// Upload documents
console.log('Starting file upload');
for (const uc of uploadConfigs) {
  await uploadDocuments(blob, containerName, uc.fromFolder, uc.blobFolder);
}

// Produce layout files for these folders (from blob storage, use urlSource, save JSON to blob storage)
console.log('Starting layout generation');
await createLayoutJson(blob, containerName, uploadConfigs, trainingClient);

const classifierName = 'monthly-report-classifier';

// Train classifier.
console.log('Starting classifier training');
await trainClassifier(
  classifierName,
  'montly report classifier',
  uploadConfigs,
  blob,
  containerName,
  trainingClient
);

// Optionally, delete blob storage to save costs.
await blob.deleteContainerIfExists(containerName);


// Testing of classifier
const testDocuments = [
  './report_documents/form_image_44.jpg',
  './report_documents/form_image_77.jpg',
  './other_documents/01122115.png',
  './other_documents/0001463282.png'
]

// Has to be done in two parts: one to request, another to retrieve.
console.log('Starting sample classification')
for (const d of testDocuments) {
  const { status, content } = await requestClassification(trainingClient, classifierName, d);
  console.log(status, content)
  if (status == 202) {
    await pollOperation(content, (result) => {
      console.log(result)
    })
  }
}






