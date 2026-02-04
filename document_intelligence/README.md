# Document Intelligence Local Deployment

This project demonstrates deploying Azure Document Intelligence (Form Recognizer) in a local Docker container, with the goal of eventually deploying to OpenShift. The primary objective is to enable Document Intelligence deployment in a sovereign cloud environment, allowing it to process protected Class C data.

## Overview

Azure Document Intelligence can be containerized and run locally or in on-premises environments. This setup uses Docker Compose to orchestrate the Form Recognizer service, with an optional nginx reverse proxy configuration for routing multiple service endpoints.

## Prerequisites

- Docker and Docker Compose installed
- Azure Document Intelligence resource with:
  - API key (`FORM_RECOGNIZER_KEY`)
  - Endpoint URI (`FORM_RECOGNIZER_ENDPOINT_URI`)

## Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
FORM_RECOGNIZER_KEY=your-api-key-here
FORM_RECOGNIZER_ENDPOINT_URI=your-endpoint-uri-here
```

### Docker Compose Services

The `docker-compose.yml` file defines a single Form Recognizer service that:
- Runs the Microsoft Azure Cognitive Services Form Recognizer container (Document API 3.0)
- Exposes the service on port 5000
- Configures verbose logging for debugging
- Requires acceptance of the EULA

## Usage

1. Ensure your `.env` file is configured with the required credentials
2. Start the services:
   ```bash
   docker-compose up -d
   ```
3. The service will be available at `http://localhost:5000`
4. View logs:
   ```bash
   docker-compose logs -f form-recognizer
   ```

## Known Limitations and Issues

### Billing Endpoint Connection

There are significant limitations when deploying Document Intelligence outside of Azure. The service is required to connect back to Azure for billing purposes. The Microsoft documentation assumes the Document Intelligence endpoint is publicly accessible; however, for BC Government deployments, the endpoint is not public and is instead behind an API Management (APIM) gateway.

**Current Status**: We were unable to successfully establish a connection to the billing endpoint through APIM. This issue was deemed low priority as it is not currently relevant to ongoing work.

**Requirements for APIM Integration**:
- The APIM key is required for connection
- The endpoint to Document Intelligence must be the one exposed through APIM (not the direct Azure endpoint)

### Future Work

If this project is picked up again in the future, the recommendation is to:
1. Contact Microsoft support to discuss the intricacies of Document Intelligence connection to Azure billing endpoints
2. Investigate APIM-specific configuration requirements for containerized Document Intelligence
3. Explore alternative billing/connection models that may be available for sovereign cloud deployments