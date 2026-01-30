import { DocumentIntelligenceClient } from "@azure-rest/ai-document-intelligence";
import { BlobStorage } from "./blobStorage.ts";
import { UploadConfig } from "./interfaces.ts";
import { pollOperation } from "./operationHandler.ts";

const generateTrainingConfig = (classifierId: string, description: string, uploadConfigs: UploadConfig[], containerUrl: string) => {
  interface DocType {
    azureBlobSource: {
      containerUrl: string; // Sas Url of container root.
      prefix: string; // Folder where this type of document is found.
    }
  }
  const docTypes: Record<string, DocType> = {};
  for (const uc of uploadConfigs) {
    // This docType defines the label the classifier issues to recognised documents.
    docTypes[uc.label] = {
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

export const trainClassifier = async (classifierName: string, description: string, uploadConfigs: UploadConfig[], blob: BlobStorage, containerName: string, client: DocumentIntelligenceClient) => {
  const containerUrl = await blob.generateSasUrl(containerName);

  const trainingConfig = generateTrainingConfig(
    classifierName,
    description,
    uploadConfigs,
    containerUrl
  );

  // Run training of classifier
  const response = await client.path('/documentClassifiers:build',).post({
    body: trainingConfig,
    queryParameters: { "api-version": "2024-11-30" },
  });


  // Poll operation status if 202 Accepted
  let operationLocation = response.headers["operation-location"] || response.headers["Operation-Location"];
  if (response.status == '202' && operationLocation) {
    // Returned operation-location header uses wrong domain.
    // Must replace with our actual Doc Intelligence endpoint (not training one)
    const docIntelligenceEndpoint = Deno.env.get("AZURE_DOCUMENT_INTELLIGENCE_TRAIN_ENDPOINT")!;
    operationLocation = operationLocation.replace(
      /https:\/\/[^/]+/,
      docIntelligenceEndpoint
    );
    await pollOperation(operationLocation, async () => {
      // Check completed classifier
      const classifier = await client.path(`/documentClassifiers/${classifierName}`).get({
        queryParameters: { "api-version": "2024-11-30" },
      })
      console.log('Classifier training results:')
      console.log(classifier.status)
      console.log(classifier.body)
    }, (result) => {
      console.error("Training failed:", result);
    });
  } else {
    console.error('Request for training unsuccessful:')
    console.error(response.status);
    console.error(response.body);
  }
}
