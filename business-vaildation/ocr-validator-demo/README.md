# OCR Validator Demo

A NestJS demo project demonstrating JSON schema validation for post-OCR invoice processing. This project showcases field-level constraints, custom validator classes, and mocked external API adapters.

## Features

- **JSON Schema Validation**: Uses AJV to validate invoice data against a JSON schema
- **DTO Validation**: Leverages class-validator decorators for type-safe validation
- **Custom Validators**: Implements reusable validator classes:
  - `DateFormatValidator`: Validates ISO 8601 date format and ensures dates are not in the future
  - `AmountRangeValidator`: Validates amount ranges and decimal precision
  - `TaxIdValidator`: Validates tax ID format
- **Mock External Adapters**: Simulates external services:
  - `OcrAdapter`: Mock OCR service that extracts invoice data from images
  - `ReferenceDataAdapter`: Mock reference data service for tax ID validation
- **Comprehensive Error Reporting**: Aggregates validation errors from multiple sources

## Project Structure

```
ocr-validator-demo/
├── src/
│   ├── main.ts                          # Application entry point
│   ├── app.module.ts                    # Root module
│   ├── validation/
│   │   ├── validation.module.ts         # Validation module
│   │   ├── dto/
│   │   │   ├── invoice.dto.ts           # Invoice DTO with decorators
│   │   │   └── line-item.dto.ts        # Line item DTO
│   │   ├── validators/
│   │   │   ├── date-format.validator.ts  # Custom date format validator
│   │   │   ├── amount-range.validator.ts # Custom amount range validator
│   │   │   └── tax-id.validator.ts      # Custom tax ID validator
│   │   └── schemas/
│   │       └── invoice.schema.json      # JSON schema definition
│   ├── adapters/
│   │   ├── adapters.module.ts           # Adapters module
│   │   ├── ocr.adapter.ts               # Mock OCR API adapter
│   │   └── reference-data.adapter.ts    # Mock reference data adapter
│   ├── controllers/
│   │   ├── validation.controller.ts     # Validation endpoints
│   │   └── ocr.controller.ts            # OCR processing endpoints
│   └── services/
│       └── validation.service.ts        # Validation orchestration service
├── package.json
├── tsconfig.json
└── README.md
```

## Installation

1. Install dependencies:
```bash
npm install
```

2. Build the project:
```bash
npm run build
```

3. Start the development server:
```bash
npm run start:dev
```

The application will start on `http://localhost:3000`

## API Endpoints

### 1. Validate Invoice Data

**POST** `/api/validation/validate`

Validates invoice data using JSON schema, DTO validation, and custom validators.

**Request Body:**
```json
{
  "invoiceNumber": "INV-2024-001",
  "date": "2024-01-15T10:30:00Z",
  "amount": 1250.50,
  "taxId": "TAX123456789",
  "vendorName": "Acme Corporation",
  "lineItems": [
    {
      "description": "Software License",
      "quantity": 1,
      "unitPrice": 1000.00
    },
    {
      "description": "Support Services",
      "quantity": 2.5,
      "unitPrice": 100.20
    }
  ],
  "currency": "USD",
  "notes": "Payment due in 30 days"
}
```

**Success Response (200):**
```json
{
  "message": "Validation successful",
  "data": { ... }
}
```

**Error Response (400):**
```json
{
  "message": "Validation failed",
  "errors": [
    {
      "field": "date",
      "message": "Date cannot be in the future",
      "value": "2025-12-31T00:00:00Z"
    }
  ],
  "schemaErrors": [...],
  "dtoErrors": [...],
  "customValidatorErrors": [...]
}
```

### 2. Get JSON Schema

**GET** `/api/validation/schema`

Returns the JSON schema used for validation.

**Response (200):**
```json
{
  "schema": {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    ...
  }
}
```

### 3. Process OCR Invoice

**POST** `/api/ocr/process`

Simulates OCR processing of an invoice image and validates the extracted data.

**Request Body:**
```json
{
  "imageData": "base64-encoded-image-data"
}
```

Or with custom data for testing:
```json
{
  "customData": {
    "invoiceNumber": "INV-2024-001",
    "date": "2024-01-15T10:30:00Z",
    "amount": 1250.50,
    "taxId": "TAX123456789",
    "vendorName": "Acme Corporation",
    "lineItems": [...]
  }
}
```

**Response (200):**
```json
{
  "ocr": {
    "data": { ... },
    "confidence": 0.95,
    "rawText": "...",
    "processingTime": 500,
    "errors": []
  },
  "validation": {
    "isValid": true,
    "errors": [],
    "schemaErrors": [],
    "dtoErrors": [],
    "customValidatorErrors": []
  }
}
```

## Field-Level Constraints

The invoice schema enforces the following constraints:

- **invoiceNumber**: Required string, 3-50 characters
- **date**: Required ISO 8601 date-time string, cannot be in the future
- **amount**: Required number, 0-999999.99, max 2 decimal places
- **taxId**: Required string, 9-15 alphanumeric characters (uppercase), validated against reference data
- **vendorName**: Required string, 2-100 characters
- **lineItems**: Required array with at least 1 item, each with:
  - **description**: Required string, 1-200 characters
  - **quantity**: Required number, 0.01-10000
  - **unitPrice**: Required number, 0-99999.99, max 2 decimal places
- **currency**: Optional string, 3-letter ISO 4217 code (default: USD)
- **notes**: Optional string, max 500 characters

## Custom Validators

### DateFormatValidator

Validates that dates are:
- Valid ISO 8601 format strings
- Not in the future

**Usage:**
```typescript
@IsValidDateFormat()
date: string;
```

### AmountRangeValidator

Validates that amounts are:
- Within the range 0-999999.99
- Have at most 2 decimal places

**Usage:**
```typescript
@IsValidAmountRange()
amount: number;
```

### TaxIdValidator

Validates that tax IDs:
- Match the pattern: 9-15 alphanumeric characters (uppercase)
- Are validated against the reference data adapter (in validation service)

**Usage:**
```typescript
@Matches(/^[A-Z0-9]{9,15}$/)
taxId: string;
```

## Mock Adapters

### OCRAdapter

Simulates an OCR service that:
- Processes invoice images
- Returns structured data with confidence scores
- Includes potential OCR errors for testing
- Supports 4 different scenarios (perfect, format errors, validation errors, missing fields)

### ReferenceDataAdapter

Simulates a reference data service that:
- Validates tax IDs against a mock database
- Returns vendor information including status (active, inactive, suspended)
- Includes mock delay to simulate API calls

**Valid Tax IDs in Mock Database:**
- `TAX123456789` - Acme Corporation (active)
- `TAX987654321` - Global Services (active)
- `TAX111222333` - Tech Solutions Inc (active)
- `TAX444555666` - Suspended Vendor LLC (suspended)
- `TAX777888999` - Inactive Company (inactive)

## Validation Flow

The validation service orchestrates multiple validation strategies:

1. **JSON Schema Validation**: Validates data structure and types against the JSON schema
2. **DTO Validation**: Uses class-validator decorators for additional constraints
3. **Custom Business Logic**: 
   - Validates tax ID against reference data
   - Checks line items sum matches total amount
   - Validates vendor status

All errors are aggregated and returned together for comprehensive feedback.

## Example Usage

### Valid Invoice

```bash
curl -X POST http://localhost:3000/api/validation/validate \
  -H "Content-Type: application/json" \
  -d '{
    "invoiceNumber": "INV-2024-001",
    "date": "2024-01-15T10:30:00Z",
    "amount": 1250.50,
    "taxId": "TAX123456789",
    "vendorName": "Acme Corporation",
    "lineItems": [
      {
        "description": "Software License",
        "quantity": 1,
        "unitPrice": 1000.00
      },
      {
        "description": "Support Services",
        "quantity": 2.5,
        "unitPrice": 100.20
      }
    ]
  }'
```

### Invalid Invoice (Future Date)

```bash
curl -X POST http://localhost:3000/api/validation/validate \
  -H "Content-Type: application/json" \
  -d '{
    "invoiceNumber": "INV-2024-001",
    "date": "2025-12-31T00:00:00Z",
    "amount": 1250.50,
    "taxId": "TAX123456789",
    "vendorName": "Acme Corporation",
    "lineItems": [
      {
        "description": "Software License",
        "quantity": 1,
        "unitPrice": 1000.00
      }
    ]
  }'
```

## Development

```bash
# Development mode with hot reload
npm run start:dev

# Build for production
npm run build

# Start production server
npm run start:prod

# Run tests
npm test
```

## Technologies Used

- **NestJS**: Progressive Node.js framework
- **TypeScript**: Type-safe JavaScript
- **class-validator**: Decorator-based validation
- **class-transformer**: Object transformation
- **AJV**: JSON schema validator
- **ajv-formats**: Additional format validators for AJV

## License

MIT

