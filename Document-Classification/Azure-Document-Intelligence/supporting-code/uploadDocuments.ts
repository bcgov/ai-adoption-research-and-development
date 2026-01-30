import { Buffer } from "node:buffer";
import { BlobStorage } from "./blobStorage.ts";

export const uploadDocuments = async (blob: BlobStorage, containerName: string, fromFolder: string, blobFolder: string = 'documents', max: number = 10) => {
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
