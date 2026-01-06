# Camunda 7 Workflows

> **Note:** This folder (`workflows/camunda7`) contains workflows for **Camunda 7**. For Camunda 8 workflows, see the `workflows/camunda8` folder.

This project contains **Camunda 7 external-task workflows** built with Node.js workers and an Express webhook server.

## Available Workflows

### 1. Azure OCR Document Processing
Sends uploaded documents to **Azure Document Intelligence** for OCR, polls for results, and returns structured data.

```
Document Upload → Prepare File → Submit to Azure OCR → Poll Results → Extract Data → Done
```

### 2. GitHub AI Agent
> **⚠️ Note:** This workflow is **incomplete** and still under development.

An **agentic workflow** powered by Google Gemini that can interact with GitHub repositories - reading files, getting repo info, creating/updating files, and creating pull requests.

```
Chat Message → AI Agent (with GitHub tools) → Response
```

## Project Structure

```
workflows/camunda/
├── bpmn/                           # BPMN workflow definitions
│   ├── ocr-demo-workflow.bpmn      # OCR document processing
│   └── github-agent-workflow.bpmn  # GitHub AI agent
│
├── workers/                        # External task workers
│   ├── client.ts                   # Shared Camunda client
│   ├── index.ts                    # Main entry (loads all workers)
│   ├── ocr/                        # OCR workflow workers
│   │   ├── index.ts
│   │   ├── readFileFromDisk.ts
│   │   ├── prepareFileData.ts
│   │   ├── submitToAzureOCR.ts
│   │   ├── extractRequestId.ts
│   │   ├── pollOCRResults.ts
│   │   ├── incrementRetryCount.ts
│   │   └── extractOCRResults.ts
│   └── githubAgent/                # GitHub Agent workers
│       ├── index.ts
│       ├── agent.ts                # Gemini AI agent logic
│       ├── prompts.ts              # System prompts
│       └── tools/
│           └── github.ts           # GitHub API tools
│
├── webhook/                        # HTTP API server
│   ├── server.ts                   # Express app entry
│   ├── ocrRoutes.ts                # /ocr-upload endpoint
│   └── agentRoutes.ts              # /agent-chat endpoint
│
├── src/                            # Shared utilities
│   ├── camunda.ts                  # Camunda config
│   └── types/
│       ├── index.ts                # OCR types
│       └── agent.ts                # Agent types
│
├── forms/                          # Camunda forms
│   └── review-ocr-form.form
│
├── deploy.ts                       # BPMN deployment script
├── docker-compose.yaml             # Camunda 7 container
└── package.json
```

## Getting Started

1) **Install dependencies**

```bash
npm install
```

2) **Create environment file**

```bash
cp env.example .env
```

Fill in the required credentials (see [Configuration Reference](#configuration-reference) below).

3) **Start Camunda 7 locally**

```bash
./camunda-start-wsl.sh
# or
docker-compose up -d
```

Camunda webapps/REST: `http://localhost:8080` (demo/demo).

4) **Deploy the BPMN workflows**

```bash
npm run build
npm run deploy
```

5) **Run workers and webhook**

```bash
npm run start:workers   # starts all external-task workers
npm run start:webhook   # starts Express API server
# or
npm start               # starts both (index.ts)
```

## Using the GitHub Agent

### Chat with the Agent

```bash
curl -X POST http://localhost:3000/agent-chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me the README.md from owner/repo"}'
```

### Request Format

```json
{
  "message": "Your question or task for the agent",
  "conversationId": "optional-id-for-tracking",
  "context": {
    "owner": "optional-default-github-owner",
    "repo": "optional-default-repo-name"
  }
}
```

### Response Format

```json
{
  "success": true,
  "response": "Agent's response text",
  "conversationId": "conv-123",
  "processInstanceId": "abc-123",
  "toolsUsed": ["get_file", "get_repo_info"]
}
```

### Available GitHub Tools

The agent has access to these GitHub operations:

| Tool | Description |
|------|-------------|
| `get_repo_info` | Get repository metadata (name, description, default branch, stars, etc.) |
| `get_file` | Read file contents from a repository |
| `create_or_update_file` | Create new files or update existing files (commits to a branch) |
| `create_pull_request` | Create a PR to merge changes between branches |

### Example Prompts

- "What's in the README.md of octocat/Hello-World?"
- "Get the repository info for facebook/react"
- "Create a file called `test.txt` with content 'Hello World' in owner/repo on branch feature/test"
- "Create a pull request from feature/test to main in owner/repo"

## Using the OCR Workflow

```bash
curl -X POST http://localhost:3000/ocr-upload -F "file=@document.pdf"
```

Supported upload formats:
- multipart/form-data (`file` field, recommended)
- binary body (`application/pdf`, `image/*`, `application/octet-stream`)
- JSON `{ "file": "<base64>", "filename": "doc.pdf" }`

## Configuration Reference

Copy `env.example` to `.env` and adjust:

### Camunda Settings
- `CAMUNDA_7_VERSION` — Docker image tag for Camunda Run
- `CAMUNDA_ADMIN_USER` / `CAMUNDA_ADMIN_PASSWORD` — admin user credentials
- `CAMUNDA_ENGINE_URL` — REST base URL (default `http://localhost:8080/engine-rest`)
- `CAMUNDA_BASIC_AUTH_USER` / `CAMUNDA_BASIC_AUTH_PASSWORD` — credentials for workers/webhook
- `WEBHOOK_PORT` — webhook listener port (default 3000)
- `CAMUNDA_WORKER_ID` — optional worker id

### Azure OCR Settings
- `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` — Azure Document Intelligence endpoint
- `AZURE_DOCUMENT_INTELLIGENCE_API_KEY` — API key

### GitHub Agent Settings
- `GEMINI_API_KEY` — Google AI API key ([get one here](https://aistudio.google.com/app/apikey))
- `GITHUB_TOKEN` — GitHub Personal Access Token ([create one here](https://github.com/settings/tokens))
- `GITHUB_DEFAULT_OWNER` — Optional default repository owner
- `GITHUB_DEFAULT_REPO` — Optional default repository name

## Scripts

- `npm run build` — compile TypeScript to `dist`
- `npm start` — start webhook + workers from compiled output
- `npm run start:workers` — run workers only
- `npm run start:webhook` — run webhook only
- `npm run deploy` — deploy BPMN to Camunda 7 REST
- `./camunda-start-wsl.sh` / `./camunda-stop-wsl.sh` — convenience wrappers for Docker Compose

## Troubleshooting

- **REST auth errors** — ensure `CAMUNDA_BASIC_AUTH_USER/PASSWORD` match the docker-compose admin user.
- **Workers not fetching tasks** — confirm Camunda is healthy (`docker-compose ps` shows healthy) and `CAMUNDA_ENGINE_URL` points to the running engine.
- **Azure errors** — verify `AZURE_DOCUMENT_INTELLIGENCE_*` env vars and file size (<50MB).
- **GitHub agent errors** — verify `GEMINI_API_KEY` and `GITHUB_TOKEN` are set correctly.
- **Deployment fails** — check BPMN path and REST URL; if auth enabled, confirm credentials.
- **Agent workflow not found** — make sure to deploy `github-agent-workflow.bpmn` using `npm run deploy`.
