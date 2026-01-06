# AI OCR Project

This project was put together using GitHub spec kit as an experiment in specification-driven development (SDD). See `.specify/` and `specs\001-doc-processing-automation` for the specification documents.

## Quick Start

### Development Environment Setup

```bash
docker compose -f ops/compose.dev.yml up -d postgres redis minio keycloak minio-init
```

### Database Setup

Generate and setup the Prisma client:

```bash
# Build shared types first
pnpm nx run shared-types:build

# Generate Prisma client
pnpm nx run api:prisma-generate

# Reset and push database schema
npx prisma migrate reset
pnpm prisma db push
```

### Start the core services:

```bash
pnpm nx serve api
pnpm nx serve ingestion-worker
```

Start the infrastructure dependencies:



### Database Management

Launch Prisma Studio for database visualization and management:

```bash
npx prisma studio
```

## Environment Management

### Reset Environment

To reset the development environment:

```bash
pnpm run reset:env
```

## API Testing Examples

### Configuration

```bash
API=http://localhost:3000/api
REQUIRE_TLS=false
```

### Authentication

Login to get an authentication token:

```bash
curl -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'
```

Example JWT token (admin user with operator and admin roles):

```bash
TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInByZWZlcnJlZF91c2VybmFtZSI6ImFkbWluIiwicm9sZXMiOlsib3BlcmF0b3IiLCJhZG1pbiJdLCJpYXQiOjE3NjU0OTU5ODgsImV4cCI6MTc2NTQ5OTU4OH0.EJGsNS1zyQ0Ycc1Ttrwd_TEmEg81JNM9_J21n8l-EX0
```

### Document Upload Examples

#### PDF Document Upload

Upload a PDF document with base64 encoded content:

```bash
FILE=sampleDocs/sample1.pdf
CHECKSUM=$(sha256sum "$FILE" | cut -d' ' -f1)
BASE64=$(base64 -w0 "$FILE")

cat <<EOF | curl -k -X POST "$API/documents" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @-
{
  "sourceChannel": "upload",
  "originalUri": "file://$FILE",
  "filename": "$(basename "$FILE")",
  "checksum": "$CHECKSUM",
  "idempotencyKey": "idem-$CHECKSUM",
  "metadata": {
    "rawContentBase64": "$BASE64"
  }
}
EOF
```

#### Invoice Image Upload (Classifies by Filename)

Upload an invoice image for OCR processing:

```bash
cat <<EOF | curl -k -X POST "$API/documents" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @-
{
  "sourceChannel": "upload",
  "originalUri": "file://sampleDocs/invoice.png",
  "filename": "$(basename "sampleDocs/invoice.png")",
  "checksum": "$(sha256sum "sampleDocs/invoice.png" | cut -d' ' -f1)",
  "idempotencyKey": "idem-$(sha256sum "sampleDocs/invoice.png" | cut -d' ' -f1)",
  "metadata": {
    "rawContentBase64": "$(base64 -w0 "sampleDocs/invoice.png")"
  }
}
EOF
```

## Documentation Guidelines Prompt

Can you add comments to important sections only in this code? Do add in-line comments. Write them accessibly as well as technically. Do not add comments to trivial code. Do not add code to test files. Make sure comments don't run long in a single line, break into new lines as necessary.
Comments should be like this e.g. "technical description. \n Explanation: accessible explanation" Also in comments if you find something incongruent or something that doesn't make sense, add a "NOTE: your finding". Go through all the files.
