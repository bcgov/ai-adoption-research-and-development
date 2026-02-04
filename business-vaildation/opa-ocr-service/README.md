# OPA OCR Service

A standalone Open Policy Agent (OPA) API service for post-OCR processing validation. This service validates OCR results using Rego policies for both data quality checks and business rules.

## Features

- **Data Quality Validation**: Checks OCR confidence thresholds, extracted text completeness, and required fields
- **Business Rules Validation**: Validates document types, field constraints, and compliance requirements
- **RESTful API**: Simple HTTP endpoints for policy evaluation
- **Flexible Integration**: Can be called by Camunda workflows, other services, or standalone requests
- **Rego Policies**: Extensible policy definitions using Rego language

## Architecture

The service consists of:

1. **OPA Server**: External OPA server (via Docker) or embedded evaluation
2. **REST API**: Express.js API endpoints for policy evaluation
3. **Rego Policies**: Policy definitions in `policies/` directory
4. **Policy Service**: TypeScript service layer that interfaces with OPA
5. **Type Definitions**: TypeScript types matching OCR result structure

## Getting Started

### Prerequisites

- Node.js 20+
- Docker (optional, for OPA server)
- OPA server (can run via Docker Compose)

### Installation

1. Install dependencies:
```bash
npm install
```

2. Configure environment variables:
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
- `OPA_SERVER_URL`: URL to OPA server (default: http://localhost:8181)
- `POLICIES_DIR`: Directory containing Rego policies (default: ./policies)
- `PORT`: API server port (default: 3001)

3. Start OPA server (using Docker Compose):
```bash
docker-compose up -d opa
```

Or start your own OPA server and point `OPA_SERVER_URL` to it.

4. Build and start the service:
```bash
npm run build
npm start
```

For development:
```bash
npm run start:dev
```

The service will start on `http://localhost:3001`

## API Endpoints

### POST /api/policy/evaluate

Evaluate OCR results against OPA policies.

**Request:**
```json
{
  "ocrResult": {
    "extractedText": "Sample extracted text...",
    "pages": [
      {
        "pageNumber": 1,
        "width": 8.5,
        "height": 11,
        "unit": "inch",
        "words": [
          {
            "content": "Sample",
            "confidence": 0.95,
            "span": { "offset": 0, "length": 6 }
          }
        ],
        "lines": [],
        "spans": []
      }
    ],
    "tables": [],
    "paragraphs": [],
    "keyValuePairs": [],
    "sections": [],
    "figures": [],
    "status": "succeeded",
    "apimRequestId": "req-123",
    "fileName": "document.pdf",
    "fileType": "pdf",
    "processedAt": "2024-01-15T10:30:00Z"
  },
  "policyPackage": "ocr.validation"  // Optional
}
```

**Response:**
```json
{
  "allowed": true,
  "result": {
    "valid": true,
    "violations": [],
    "warnings": [],
    "dataQualityScore": 0.95,
    "businessRuleCompliance": true
  }
}
```

### GET /api/policy/policies

List all available policy packages and rules.

**Response:**
```json
{
  "policies": ["data-quality", "business-rules", "main"],
  "count": 3
}
```

### GET /api/policy/health

Health check for OPA service connectivity.

**Response:**
```json
{
  "healthy": true,
  "opaConnected": true
}
```

## Policy Structure

Policies are defined in Rego files in the `policies/` directory:

- **data-quality.rego**: Data quality validation rules
- **business-rules.rego**: Business rule validation
- **main.rego**: Main entry point that combines all policies

### Policy Packages

- `ocr.validation.data_quality`: Data quality checks
- `ocr.validation.business_rules`: Business rules validation
- `ocr.validation`: Main validation package (combines all)

## Integration with Camunda Workflows

To integrate with Camunda workflows, create a worker that calls this service:

```typescript
// In your Camunda worker
const response = await axios.post('http://localhost:3001/api/policy/evaluate', {
  ocrResult: ocrResult,
});

if (response.data.allowed) {
  // Proceed with workflow
} else {
  // Handle violations
  console.error('Policy violations:', response.data.result.violations);
}
```

## Development

### Project Structure

```
opa-ocr-service/
├── src/
│   ├── main.ts                    # Application entry point
│   ├── controllers/
│   │   └── policy.controller.ts   # REST endpoints
│   ├── services/
│   │   ├── opa.service.ts         # OPA client integration
│   │   └── policy.service.ts      # Policy evaluation orchestration
│   ├── types/
│   │   └── ocr-result.types.ts   # OCR result type definitions
│   └── dto/
│       └── policy-evaluation.dto.ts # Request/response DTOs
├── policies/                      # Rego policy files
│   ├── data-quality.rego
│   ├── business-rules.rego
│   └── main.rego
├── package.json
├── tsconfig.json
└── README.md
```

### Building

```bash
npm run build
```

### Type Checking

```bash
npm run type-check
```

## Docker

### Using Docker Compose

Start both OPA server and the service:

```bash
docker-compose up -d
```

### Building Docker Image

```bash
docker build -t opa-ocr-service .
```

## Configuration

Environment variables:

- `OPA_SERVER_URL`: URL to OPA server (default: http://localhost:8181)
- `POLICIES_DIR`: Directory containing Rego policy files (default: ./policies)
- `PORT`: API server port (default: 3001)

## Policy Examples

### Data Quality Policy

```rego
package ocr.validation.data_quality

default allowed = false

allowed {
    input.ocrResult.status == "succeeded"
    count(input.ocrResult.extractedText) > 0
    some page in input.ocrResult.pages
    some word in page.words
    word.confidence > 0.7
}
```

### Business Rules Policy

```rego
package ocr.validation.business_rules

default allowed = false

allowed {
    count(input.ocrResult.keyValuePairs) > 0
    input.ocrResult.fileType in ["pdf", "image"]
    input.ocrResult.fileName != ""
}
```

## License

MIT

