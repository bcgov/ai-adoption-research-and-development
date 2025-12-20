# Camunda OCR Workflow - Project Overview

> **Note:** This folder (`workflows/camunda8`) contains workflows for **Camunda 8**. For Camunda 7 workflows, see the `workflows/camunda7` folder.

## What is This?

This project is an **automated document processing system** that uses **Camunda 8** (a workflow automation platform) to process documents through **Azure's OCR (Optical Character Recognition)** service. Think of it as a pipeline that takes documents (PDFs, images) and extracts text and structured data from them automatically.

## The Big Picture

```
Document Upload → Read File → Submit to Azure OCR → Poll for Results → Extract Data → Done!
```

## Components Breakdown

### 1. **Docker Compose Setup**

#### Lightweight Configuration (`docker-compose.yaml`)

This file defines a local development environment with three main services:

- **Orchestration Service** (Camunda Platform)
  - **Zeebe**: The workflow engine that executes your business processes
  - **Operate**: Web UI to monitor and manage running workflows
  - **Tasklist**: Web UI to view and complete human tasks
  - Runs on ports: `26500` (Zeebe), `8088` (Operate/Tasklist)
  - Default login: `demo` / `demo`

- **Connectors Service**
  - Handles integrations with external systems (Azure, AWS, etc.)
  - Runs on port `8086`
  - Uses secrets from `connector-secrets.txt` for API keys

- **Elasticsearch**
  - Database that stores workflow execution history and data
  - Runs on ports `9200` and `9300`
  - Used by Camunda to index and search process data

#### Desktop Modeler (Recommended for Development)

**Camunda Desktop Modeler** is a free, open-source desktop application for modeling BPMN, DMN, and Camunda Forms. It's the recommended tool for local development as it requires no Docker setup or authentication.

**Installation:**

1. **Download Desktop Modeler:**
   - Visit: https://camunda.com/download/modeler/
   - Download the version for your operating system (Windows, macOS, or Linux)
   - Install the application

2. **Open your workflow files:**
   - Desktop Modeler can open `.bpmn`, `.dmn`, and form files directly
   - Simply double-click `ocr-demo-workflow.bpmn` or open it from Desktop Modeler

**Deploying to Camunda 8:**

Once you've created or modified a workflow in Desktop Modeler, you can deploy it to your local Camunda instance:

1. **Open Desktop Modeler** and load your BPMN file

2. **Click the deployment icon** (rocket symbol) in the toolbar

3. **Select "Camunda 8 Self-Managed"**

4. **Configure the connection:**
   - **Cluster endpoint**: `http://localhost:26500`
   - **Authentication**: Select **None** (the lightweight configuration uses basic auth with unprotected API)

5. **Click "Deploy"**

Your workflow will be deployed to the local Camunda instance and available for execution.

**Alternative Deployment Method:**

You can also use the included `deploy.js` script:
```bash
npm run deploy
```

This script uses the `@camunda8/sdk` to deploy the BPMN file programmatically.

**Resources:**
- [Desktop Modeler Documentation](https://docs.camunda.io/docs/components/modeler/desktop-modeler/)
- [Desktop Modeler Deployment Guide](https://docs.camunda.io/docs/components/modeler/desktop-modeler/deploy/)

### 2. **Workflow Definition** (`ocr-demo-workflow.bpmn`)

This is a **BPMN (Business Process Model and Notation)** file that defines the workflow steps:

1. **Start**: Single start event (can be triggered manually with filePath or via webhook)
2. **Gateway**: Routes to Read File task if filePath exists, otherwise goes directly to Prepare File Data
3. **Read File** (optional): Reads a document from disk and converts to base64
4. **Prepare File Data**: Formats the file for Azure OCR (handles both webhook uploads and file reads)
5. **Submit to Azure OCR**: Sends the document to Azure's Document Intelligence API
6. **Extract Request ID**: Extracts the APIM request ID from the HTTP response
7. **Check Submission**: Validates if submission was successful (status code 202)
8. **Poll OCR Results**: Checks if Azure has finished processing (with retry logic)
9. **Increment Retry Count**: Tracks polling attempts (max 20 retries)
10. **Extract OCR Results**: Processes the results and extracts structured data
11. **End**: Workflow completes (success, error, or timeout)

### 3. **Node.js Workers** (`workers/`)

Workers are background processes that execute specific tasks in the workflow. They "listen" for tasks assigned by Camunda and execute them:

- **`readFileFromDisk.js`**: Reads a file from the filesystem and converts it to base64
- **`prepareFileData.js`**: Prepares file data for Azure OCR (handles webhook uploads and file reads)
- **`submitToAzureOCR.js`**: Sends the document to Azure Document Intelligence API
- **`extractRequestId.js`**: Extracts APIM request ID from HTTP response headers
- **`pollOCRResults.js`**: Checks the status of the OCR job and retrieves results
- **`incrementRetryCount.js`**: Increments the retry counter for polling operations
- **`extractOCRResults.js`**: Extracts and structures OCR results from Azure response
- **`index.js`**: Starts all workers together

### 4. **Webhook Server** (`webhook/server.js`)

An Express.js server that:
- Listens for HTTP POST requests on port `3000` (default, configurable via `WEBHOOK_PORT`)
- Accepts file uploads at `/ocr-upload`
- Supports multiple upload formats:
  1. **multipart/form-data** (standard file upload with field name `file`) - Recommended
  2. **Direct binary upload** (application/pdf, image/jpeg, image/png, application/octet-stream)
  3. **JSON with base64 encoded file** (for programmatic integrations)
- Starts a new Camunda workflow instance when a file is uploaded
- Includes a health check endpoint at `/health`
- Allows external systems to trigger the OCR process via API

**Example Usage:**

```bash
# Using curl with multipart/form-data (recommended)
curl -X POST http://localhost:3000/ocr-upload \
  -F "file=@document.pdf"

# Using curl with direct binary upload
curl -X POST http://localhost:3000/ocr-upload \
  -H "Content-Type: application/pdf" \
  --data-binary @document.pdf

# Using curl with JSON (base64 encoded)
curl -X POST http://localhost:3000/ocr-upload \
  -H "Content-Type: application/json" \
  -d '{"file": "base64encodedfiledata...", "filename": "document.pdf"}'
```

### 5. **Deployment Script** (`deploy.js`)

A utility script that:
- Connects to the Camunda Zeebe engine using `@camunda8/sdk`
- Deploys the BPMN workflow file using the `deployResource()` method
- Makes the workflow available for execution

### 6. **Helper Scripts**

- **`camunda-start-wsl.sh`**: Convenience script to start all Docker services
- **`camunda-stop-wsl.sh`**: Convenience script to stop all Docker services

## How It Works (Step by Step)

1. **Start the Infrastructure**
   ```bash
   ./camunda-start-wsl.sh
   # or
   docker-compose up -d
   ```
   This starts Camunda, Connectors, and Elasticsearch in Docker containers.

2. **Deploy the Workflow**
   ```bash
   npm run deploy
   ```
   This uploads the BPMN workflow definition to Camunda.

3. **Start the Workers**
   ```bash
   npm start
   # or
   npm run start:workers
   ```
   This starts all the Node.js workers that will execute workflow tasks.

4. **Start the Webhook Server** (optional, if you want to accept file uploads)
   ```bash
   npm run start:webhook
   ```

5. **Trigger a Workflow**
   - **Via Webhook** (recommended): POST a file to `http://localhost:3000/ocr-upload`
     ```bash
     curl -X POST http://localhost:3000/ocr-upload -F "file=@your-document.pdf"
     ```
   - **Via Camunda Operate UI**: Go to `http://localhost:8088`, log in, and manually start a process instance
   - **Programmatically**: Use the Zeebe client to create a process instance

6. **Monitor Progress**
   - View running workflows in **Operate**: `http://localhost:8088`
   - View tasks in **Tasklist**: `http://localhost:8088/tasklist`

## Configuration

### Environment Variables

Create a `.env` file (copy from `env.example`) with:

- `CAMUNDA_VERSION`: Version of Camunda to use (default: `8.8.7`)
- `CAMUNDA_CONNECTORS_VERSION`: Version of connectors (default: `8.8.4`)
- `ELASTIC_VERSION`: Version of Elasticsearch (default: `8.16.0`)

### Azure OCR Credentials

Set these environment variables for Azure Document Intelligence:

- `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT`: Your Azure endpoint URL
- `AZURE_DOCUMENT_INTELLIGENCE_API_KEY`: Your Azure API key

### Connector Secrets

Edit `connector-secrets.txt` to add secrets for any connectors you use (currently mostly examples).

## Project Structure

```
workflows/cam/
├── docker-compose.yaml          # Docker services configuration
├── ocr-demo-workflow.bpmn       # Workflow definition
├── package.json                 # Node.js dependencies
├── index.js                     # Main entry point (starts workers + webhook)
├── deploy.js                    # Deploys workflow to Camunda
├── env.example                  # Environment variables template
├── connector-secrets.txt        # Connector API keys/secrets
├── camunda-start-wsl.sh         # Start script
├── camunda-stop-wsl.sh          # Stop script
├── workers/                     # Worker implementations
│   ├── index.js
│   ├── readFileFromDisk.js
│   ├── prepareFileData.js
│   ├── submitToAzureOCR.js
│   ├── extractRequestId.js
│   ├── pollOCRResults.js
│   ├── incrementRetryCount.js
│   └── extractOCRResults.js
└── webhook/                     # Webhook server
    └── server.js
```

## Key Technologies

- **Camunda 8**: Workflow automation platform
- **Zeebe**: Distributed workflow engine
- **@camunda8/sdk**: Official Camunda 8 Node.js SDK (replaces deprecated zeebe-node)
- **Node.js**: Runtime for workers and webhook server
- **Express.js**: Web framework for webhook server
- **Azure Document Intelligence**: Cloud OCR service
- **Docker Compose**: Container orchestration
- **Elasticsearch**: Search and analytics engine

## Use Cases

This workflow is useful for:
- Automatically extracting text from scanned documents
- Processing invoices, receipts, forms
- Converting paper documents to digital data
- Batch processing large volumes of documents
- Integrating OCR into larger business processes

## Next Steps

1. Set up your Azure Document Intelligence credentials
2. Start the Docker services
3. Deploy the workflow
4. Start the workers
5. Upload a test document via webhook or Operate UI
6. Monitor the workflow execution in Operate

## Troubleshooting

- **Workers can't connect**: Make sure Camunda is running and accessible on port `26500`
- **Azure OCR fails**: Check your `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` and `AZURE_DOCUMENT_INTELLIGENCE_API_KEY` environment variables
- **Docker services won't start**: Check Docker is running and ports aren't already in use
- **Workflow not found**: Make sure you've run `npm run deploy` to deploy the BPMN file

