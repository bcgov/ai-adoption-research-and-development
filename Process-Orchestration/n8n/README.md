# n8n Workflows - Project Overview

> **Note:** This folder (`Process-Orchestration/n8n`) contains workflows for **n8n**, a workflow automation platform. These workflows demonstrate document processing and AI agent automation capabilities.

## What is This?

This project contains two n8n workflows that showcase different automation capabilities:

1. **Azure OCR Document Processing** - An automated document processing system that extracts text and structured data from documents using Azure's OCR service
2. **Gemini AI Agent** - An AI-powered development automation agent that can process Trello tasks and implement changes in GitHub repositories

## Workflows Overview

### 1. Azure OCR Document Processing (`ocr-demo-workflow.json`)

An end-to-end document processing workflow that uses Azure Document Intelligence to extract text, tables, key-value pairs, and other structured data from PDFs and images.

#### The Big Picture

```
File Upload (Webhook) → Prepare File Data → Submit to Azure OCR → Poll for Results → Extract Data → Return Response
```

#### Workflow Steps

1. **Webhook - File Upload**
   - Accepts HTTP POST requests at `/ocr-upload`
   - Supports multiple upload formats:
     - **multipart/form-data** (standard file upload)
     - **Direct binary upload** (application/pdf, image/*)
     - **JSON with base64 encoded file**
   - Configured with `rawBody: true` to handle binary data properly

2. **Prepare File Data**
   - Processes incoming file data from various sources
   - Handles binary data, base64 strings, and file metadata
   - Extracts filename, content type, and file type
   - Validates PDF signatures
   - Converts data to the format required by Azure OCR

3. **Submit to Azure OCR**
   - Sends document to Azure Document Intelligence API
   - Uses the `prebuilt-layout` model with `keyValuePairs` feature
   - Sends binary data with appropriate Content-Type header
   - Includes API key authentication

4. **Extract Request ID**
   - Extracts the `apim-request-id` from HTTP response headers
   - Validates submission status code (expects 202)
   - Preserves file metadata for later use

5. **Check Submission Success**
   - Validates that submission was successful (status code 202)
   - Routes to error response if submission failed

6. **Wait Before First Poll**
   - Initial wait period before checking OCR results
   - Allows Azure time to start processing

7. **Poll OCR Results**
   - Polls Azure API for processing results using the request ID
   - Checks if processing is complete

8. **Check OCR Status**
   - Validates if processing status is "running" or "succeeded"
   - Routes to retry loop if still running
   - Routes to extraction if complete

9. **Increment Retry Count**
   - Tracks polling attempts
   - Prevents infinite loops

10. **Check Max Retries**
    - Validates retry count (max 20 retries)
    - Routes to timeout response if exceeded
    - Routes to retry wait if under limit

11. **Wait Before Retry**
    - Waits 10 seconds before next poll attempt
    - Prevents excessive API calls

12. **Extract OCR Results**
    - Extracts structured data from Azure response:
      - `extractedText`: Full text content
      - `pages`: Page-level information
      - `tables`: Extracted tables
      - `paragraphs`: Document paragraphs
      - `keyValuePairs`: Key-value pairs (forms, invoices, etc.)
      - `sections`: Document sections
      - `figures`: Images and figures
    - Includes metadata: fileName, fileType, apimRequestId, processedAt

13. **Return Success/Error/Timeout Response**
    - Returns JSON response to webhook caller
    - Includes all extracted data or error information

#### Usage

**Via Webhook (Recommended):**
```bash
# Using curl with multipart/form-data
curl -X POST http://your-n8n-instance/webhook/ocr-upload \
  -F "file=@document.pdf"

# Using curl with direct binary upload
curl -X POST http://your-n8n-instance/webhook/ocr-upload \
  -H "Content-Type: application/pdf" \
  --data-binary @document.pdf

# Using curl with JSON (base64 encoded)
curl -X POST http://your-n8n-instance/webhook/ocr-upload \
  -H "Content-Type: application/json" \
  -d '{"file": "base64encodedfiledata...", "filename": "document.pdf"}'
```

**Response Format:**
```json
{
  "success": true,
  "status": "succeeded",
  "apimRequestId": "...",
  "fileName": "document.pdf",
  "fileType": "pdf",
  "extractedText": "...",
  "pages": [...],
  "tables": [...],
  "paragraphs": [...],
  "keyValuePairs": [...],
  "sections": [...],
  "figures": [...],
  "processedAt": "2024-01-01T12:00:00.000Z"
}
```

#### Use Cases

- Automatically extracting text from scanned documents
- Processing invoices, receipts, and forms
- Converting paper documents to digital data
- Extracting structured data (tables, key-value pairs) from documents
- Batch processing large volumes of documents

---

### 2. Gemini AI Agent (`gemini-agent.json`)

An AI-powered development automation agent that uses Google Gemini to automate development workflows by processing Trello automation tasks and implementing changes in GitHub repositories.

#### The Big Picture

```
Chat Interface → AI Agent (Gemini) → Trello Tools → GitHub Tools → Implementation → Pull Request
```

#### Workflow Components

1. **Example Chat (Chat Trigger)**
   - Public chat interface for interacting with the AI agent
   - Welcome message: "Hi there! 👋"
   - Title: "Your first AI Agent 🚀"
   - Subtitle: "This is for demo purposes. Try me out !"
   - Response mode: Last node

2. **Your First AI Agent (AI Agent Node)**
   - Core AI agent powered by Google Gemini
   - System prompt defines the agent as a "Developer AI Agent"
   - Capabilities:
     - Search Trello for automation tasks
     - Extract task descriptions from Trello cards
     - Work with GitHub repositories
     - Create pull requests
   - Default repository: `YOUR_USERNAME/YOUR_REPO`

3. **Connect Gemini (Language Model)**
   - Google Gemini language model connection
   - Temperature: 0 (deterministic responses)
   - Provides the AI reasoning capability

4. **Conversation Memory (Buffer Window Memory)**
   - Maintains conversation context
   - Context window: 30 messages
   - Enables multi-turn conversations

5. **Trello Tools**
   - **Get Trello Cards**: Retrieves cards from a specific Trello list (ID: `YOUR_TRELLO_LIST_ID`)
   - **Get Trello Card Details**: Gets full details of a card including:
     - Name, description, labels
     - List ID, board ID, URL
     - Due date, start date

6. **GitHub Tools**
   - **Get GitHub Repo Info**: Retrieves repository information (default branch, latest commit SHA)
   - **Get Github Branch**: Gets branch details including SHA
   - **Create Github Branch**: Creates a new branch for changes
   - **Get File Contents from Github**: Retrieves file contents before modification
   - **Get GitHub File**: Alternative file retrieval method
   - **Create/Update GitHub File**: Creates or updates files in the repository
   - **Create Github Pull Request**: Creates a PR with changes

7. **OpenRouter Chat Model** (Alternative/Unused)
   - Alternative language model option
   - Not currently connected in the workflow

8. **Structured Output Parser** (Unused)
   - Structured output parsing capability
   - Not currently connected in the workflow

#### Agent Capabilities

The AI agent is designed to:

1. **Find Automation Tasks**
   - Search Trello for cards labeled 'automation'
   - Extract task descriptions from those cards

2. **Implement Changes**
   - Check if files exist before creating them
   - Read existing files before modifying them
   - Generate appropriate code/files based on task descriptions
   - Create or update files in GitHub repositories

3. **Create Pull Requests**
   - Create new branches for changes (format: `automation/trello-{card-name}`)
   - Commit changes to the branch
   - Create pull requests linking back to Trello cards

4. **Answer Questions**
   - Respond to general questions using available tools
   - Provide information about repositories, files, and cards

#### Workflow Process

When processing automation tasks:

1. **Get Trello List of Cards** - Retrieves cards from the automation list
2. **Get Trello Card Details** - For each card, gets full description
3. **Get GitHub Repo Info** - Gets repository details (default branch, etc.)
4. **Get Github Branch** - Retrieves main branch and extracts SHA
5. **Create Github Branch** - Creates new branch (e.g., `automation/trello-{card-name}`)
6. **Get File Contents from Github** - Pulls existing files that need modification
7. **Analyze & Generate** - AI analyzes task and generates code/files
8. **Create/Update GitHub File** - Adds or modifies files on the new branch
9. **Create GitHub Pull Request** - Creates PR linking back to Trello card

#### Configuration

**Credentials Required:**
- **Google Gemini (PaLM) API**: For the AI language model
- **Trello API**: For accessing Trello cards and lists
- **GitHub API**: For repository operations (two accounts configured)


#### Usage

**Via Chat Interface:**
1. Access the public chat interface URL
2. Start a conversation with the agent
3. Ask it to:
   - "Process automation tasks from Trello"
   - "Find Trello cards with automation label"
   - "Create a new file in the repository"
   - "Update an existing file"
   - "Create a pull request for changes"

**Example Interactions:**
- "Find all automation tasks in Trello and implement them"
- "Get the details of Trello card [card-id]"
- "Create a new file `src/utils.js` with a helper function"
- "Update the README.md file to include new information"

#### Use Cases

- Automating development workflows from Trello task cards
- Implementing code changes based on task descriptions
- Creating pull requests automatically
- Code generation and file management
- Development task automation
- Repository maintenance and updates

---

## Key Technologies

- **n8n**: Workflow automation platform
- **Azure Document Intelligence**: Cloud OCR service
- **Google Gemini**: AI language model
- **Trello API**: Task management integration
- **GitHub API**: Repository and code management
- **LangChain**: AI agent framework (via n8n nodes)

## Project Structure

```
Process-Orchestration/n8n/
├── ocr-demo-workflow.json      # Azure OCR document processing workflow
├── gemini-agent.json           # Gemini AI agent workflow
└── README.md                   # This file
```

## Deployment

### Prerequisites

1. **n8n Instance**: Running n8n (self-hosted or cloud)
2. **Azure Document Intelligence**: Account with API key and endpoint
3. **Google Gemini API**: API key for Gemini model
4. **Trello API**: API key and token
5. **GitHub API**: Personal access token or OAuth token

### Importing Workflows

1. **Open n8n**: Access your n8n instance
2. **Import Workflow**: 
   - Click "Workflows" → "Import from File"
   - Select the JSON workflow file (`ocr-demo-workflow.json` or `gemini-agent.json`)
3. **Configure Credentials**:
   - Set up Azure API credentials for OCR workflow
   - Set up Google Gemini, Trello, and GitHub credentials for AI agent workflow
4. **Update Configuration**:
   - Update API endpoints and keys as needed
   - Configure webhook URLs
   - Set repository and Trello list IDs
5. **Activate Workflow**: Toggle the workflow to "Active"

### Webhook URLs

After importing, n8n will provide webhook URLs:
- OCR workflow: `https://your-n8n-instance/webhook/ocr-upload`
- AI Agent: `https://your-n8n-instance/webhook/chat-trigger-id`

## Troubleshooting

### OCR Workflow Issues

- **File upload fails**: Check webhook configuration and ensure `rawBody: true` is set
- **Azure OCR fails**: Verify API key and endpoint URL are correct
- **Polling timeout**: Increase max retries or wait time if documents are large
- **Binary data issues**: Ensure files are properly encoded (base64 or binary)

### AI Agent Issues

- **Agent can't access Trello**: Check Trello API credentials and list ID
- **GitHub operations fail**: Verify GitHub API token has appropriate permissions
- **AI responses unclear**: Adjust temperature or system prompt in agent configuration
- **Memory issues**: Increase context window length if conversations are long

## Next Steps

1. **OCR Workflow**:
   - Configure your Azure Document Intelligence credentials
   - Test with sample documents
   - Customize extraction fields based on your needs

2. **AI Agent Workflow**:
   - Set up Trello board and list for automation tasks
   - Configure GitHub repository access
   - Test with sample automation tasks
   - Customize agent system prompt for your use case

## Additional Resources

- [n8n Documentation](https://docs.n8n.io/)
- [Azure Document Intelligence](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/)
- [Google Gemini API](https://ai.google.dev/)
- [Trello API](https://developer.atlassian.com/cloud/trello/)
- [GitHub API](https://docs.github.com/en/rest)

