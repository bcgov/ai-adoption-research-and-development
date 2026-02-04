# Temporal OCR Workflow

A Temporal workflow implementation for Azure Document Intelligence OCR processing, similar to the n8n OCR workflow.

## Overview

This workflow processes documents through Azure Document Intelligence OCR with:
- File data preparation and validation
- Azure OCR submission
- Polling with retry logic (up to 20 retries, 10-second intervals)
- Structured result extraction

## Architecture

- **Workflow** (`src/workflow.ts`): Orchestrates the OCR process with deterministic logic
- **Activities** (`src/activities.ts`): Handle non-deterministic operations (HTTP calls, file processing)
- **Worker** (`src/worker.ts`): Executes workflows and activities
- **Client** (`src/client.ts`): Triggers workflow executions

## Prerequisites

- Node.js 18+ and npm
- Temporal server (local or remote)
- Azure Document Intelligence account with API key

## Setup

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your Azure credentials and Temporal connection details
   ```

3. **Start Temporal server and Web UI (if running locally):**
   ```bash
   docker-compose up -d
   ```
   
   This will start:
   - Temporal server on port `7233` (gRPC)
   - Temporal Web UI on port `8088` (http://localhost:8088)
   - PostgreSQL database on port `5432`

4. **Build the project:**
   ```bash
   npm run build
   ```

5. **Start the worker:**
   ```bash
   npm start
   # Or for development with auto-reload:
   npm run dev
   ```

6. **Trigger a workflow (in a separate terminal):**
   ```bash
   npm run example
   ```
   
   This will start a sample OCR workflow that you can view in the Temporal Web UI.

## Usage

### Viewing Workflows in the Web UI

1. Make sure Temporal server and worker are running:
   ```bash
   # Terminal 1: Start Temporal server (if using docker-compose)
   docker-compose up -d
   
   # Terminal 2: Start the worker
   npm run dev
   ```

2. Open the Temporal Web UI: http://localhost:8088

3. **Important**: Workflows won't appear until you trigger them. The worker listens for executions but doesn't create workflows automatically.

### Starting a Workflow

Use the client to trigger a workflow execution:

```typescript
import { startOCRWorkflow } from './src/client';

const result = await startOCRWorkflow({
  binaryData: 'base64-encoded-file-data',
  fileName: 'document.pdf',
  fileType: 'pdf',
  contentType: 'application/pdf'
});
```

### Quick Start Example

Run the example script to trigger a sample workflow:

```bash
npm run example
```

This will:
1. Start an OCR workflow with sample PDF data
2. Wait for the workflow to complete
3. Display the results
4. Show you the workflow ID to view in the Web UI

After running this, you should see the workflow appear in the Temporal Web UI at http://localhost:8088

### Workflow Input

```typescript
interface OCRWorkflowInput {
  binaryData: string;        // Base64-encoded file data
  fileName?: string;         // Optional file name
  fileType?: 'pdf' | 'image'; // Optional file type
  contentType?: string;      // Optional content type
}
```

### Workflow Output

```typescript
interface OCRResult {
  success: boolean;
  status: string;
  apimRequestId: string;
  fileName: string;
  fileType: string;
  extractedText: string;
  pages: Page[];
  tables: Table[];
  paragraphs: Paragraph[];
  keyValuePairs: KeyValuePair[];
  sections: Section[];
  figures: Figure[];
  processedAt: string;
}
```

## Workflow Flow

1. **Prepare File Data**: Validates and processes binary data
2. **Submit to Azure OCR**: POST request to Azure Document Intelligence API
3. **Extract Request ID**: Extracts `apim-request-id` from response headers
4. **Check Submission**: Validates status code (must be 202)
5. **Wait**: 5 seconds before first poll
6. **Poll Loop**:
   - Poll OCR results
   - If status is "running":
     - Increment retry count
     - If retry count >= 20, throw timeout error
     - Wait 10 seconds
     - Continue polling
   - Else: break loop
7. **Extract Results**: Parse and structure OCR response
8. **Return Result**: Return structured OCR data

## Configuration

### Environment Variables

- `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT`: Azure endpoint URL
- `AZURE_DOCUMENT_INTELLIGENCE_API_KEY`: Azure API key
- `TEMPORAL_ADDRESS`: Temporal server address (default: `localhost:7233`)
- `TEMPORAL_NAMESPACE`: Temporal namespace (default: `default`)
- `TEMPORAL_TASK_QUEUE`: Task queue name (default: `ocr-processing`)

### Temporal Web UI

The Temporal Web UI is available at **http://localhost:8088** when running with docker-compose.

The Web UI allows you to:
- View workflow executions
- Monitor workflow status and history
- Inspect activity results
- Debug workflow issues
- View task queue status

### Retry Configuration

- **Max Retries**: 20
- **Wait Before First Poll**: 5 seconds
- **Wait Between Retries**: 10 seconds

## Development

```bash
# Type checking
npm run type-check

# Build
npm run build

# Development mode (auto-reload)
npm run dev
```

## Project Structure

```
temporal/
├── package.json
├── tsconfig.json
├── .env.example
├── README.md
├── docker-compose.yaml
└── src/
    ├── types.ts          # TypeScript interfaces
    ├── activities.ts     # Activity implementations
    ├── workflow.ts       # Workflow definition
    ├── worker.ts         # Worker setup
    └── client.ts         # Workflow client
```

## Error Handling

The workflow handles:
- **Submission failures**: Returns error if status code is not 202
- **Timeout**: Returns error if max retries (20) exceeded
- **API errors**: Propagates Azure API errors

## See Also

- [n8n OCR Workflow](../n8n/ocr-demo-workflow.json)
- [Camunda 7 OCR Workflow](../camunda7/)
- [Camunda 8 OCR Workflow](../camunda8/)

