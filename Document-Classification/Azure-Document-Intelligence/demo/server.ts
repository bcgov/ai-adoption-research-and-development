// Minimal Deno server for demo file upload/classification
import { Buffer } from "node:buffer";
import { load } from "https://deno.land/std@0.224.0/dotenv/mod.ts";
await load({ envPath: "../.env" });

const apiKey = Deno.env.get("AZURE_DOCUMENT_INTELLIGENCE_API_KEY")!;
const trainEndpoint = Deno.env.get("AZURE_DOCUMENT_INTELLIGENCE_TRAIN_ENDPOINT")!;
const classifierName = "monthly-report-classifier";

// Import DocumentIntelligence client as in your main code
import DocumentIntelligence, { DocumentIntelligenceClient } from "@azure-rest/ai-document-intelligence";
import { pollOperation } from "../supporting-code/operationHandler.ts";
const trainingClient = DocumentIntelligence(trainEndpoint, { key: apiKey }, {
  credentials: { apiKeyHeaderName: "api-key" }
});

async function requestClassificationBuffer(client: DocumentIntelligenceClient, classifierName: string, fileBuffer: Buffer) {
  const base64String = fileBuffer.toString('base64');
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

async function handleClassifyRequest(req: Request): Promise<Response> {
  const formData = await req.formData();
  const file = formData.get("file");
  if (!(file instanceof File)) {
    return new Response(JSON.stringify({ error: "No file uploaded" }), { status: 400 });
  }
  const fileBuffer = Buffer.from(await file.arrayBuffer());
  // Use the same logic as requestClassification, but inline for demo simplicity
  const response = await requestClassificationBuffer(trainingClient, classifierName, fileBuffer);
  console.log(response)
  if (response.status == '202') {
    // Poll for result (simple, not production robust)
    return await new Promise<Response>((resolve) => {
      pollOperation(response.content, (result) => {
        console.log(result)
        resolve(new Response(JSON.stringify(result), { headers: { "Content-Type": "application/json" } }));
      });
    });
  }
  return new Response(JSON.stringify(response.error), { headers: { "Content-Type": "application/json" }, status: response.status });
}



Deno.serve({ port: 8081 }, async (req) => {
  const url = new URL(req.url);
  if (req.method === "POST" && url.pathname === "/demo/classify") {
    return await handleClassifyRequest(req);
  }
  if (req.method === "GET" && url.pathname === "/demo/demo.js") {
    return new Response(await Deno.readTextFile("./demo/demo.js"), { headers: { "Content-Type": "application/javascript" } });
  }
  if (req.method === "GET" && url.pathname === "/demo/demo.html") {
    return new Response(await Deno.readTextFile("./demo/demo.html"), { headers: { "Content-Type": "text/html" } });
  }
  // Default: serve HTML
  if (url.pathname === "/demo" || url.pathname === "/demo/") {
    return Response.redirect(`${url.origin}/demo/demo.html`, 302);
  }
  return new Response("Not found", { status: 404 });
});
