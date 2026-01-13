"""Azure client initialization and configuration."""

import os
from typing import Optional

from azure.ai.documentintelligence import (
    DocumentIntelligenceClient,
    DocumentIntelligenceAdministrationClient,
)
from azure.core.credentials import AzureKeyCredential
from azure.core.pipeline import PipelineRequest, PipelineResponse
from azure.core.pipeline.policies import HTTPPolicy
from azure.storage.blob import BlobServiceClient


class APIMSubscriptionKeyPolicy(HTTPPolicy):
    """Custom policy to add APIM subscription key with custom header name"""

    def __init__(self, subscription_key: str, header_name: str = "api-key", verbose: bool = False):
        self.subscription_key = subscription_key
        self.header_name = header_name
        self.verbose = verbose

    def send(self, request: PipelineRequest) -> PipelineResponse:
        # Always add the subscription key with custom header name to ALL requests
        # This includes initial requests AND polling requests for long-running operations
        request.http_request.headers[self.header_name] = self.subscription_key

        # Ensure x-ms-client-request-id is present (required by Azure SDK polling)
        if "x-ms-client-request-id" not in request.http_request.headers:
            import uuid
            request.http_request.headers["x-ms-client-request-id"] = str(uuid.uuid4())

        # Remove the default header if it exists
        if "Ocp-Apim-Subscription-Key" in request.http_request.headers:
            del request.http_request.headers["Ocp-Apim-Subscription-Key"]

        # Debug logging AFTER adding headers
        if self.verbose:
            print(f"\n=== HTTP REQUEST ===")
            print(f"URL: {request.http_request.url}")
            print(f"Method: {request.http_request.method}")
            print(f"Headers: {dict(request.http_request.headers)}")
            print("=" * 50)

        # Continue with the pipeline
        response = self.next.send(request)

        # Debug response
        if self.verbose:
            print(f"\n=== HTTP RESPONSE ===")
            print(f"Status: {response.http_response.status_code}")
            print(f"Reason: {response.http_response.reason}")
            print(f"Response Headers: {dict(response.http_response.headers)}")

            # Try to show response body for debugging
            if hasattr(response.http_response, 'text') and callable(response.http_response.text):
                try:
                    body_text = response.http_response.text()[:500]  # First 500 chars
                    if body_text:
                        print(f"Response Body (first 500 chars): {body_text}")
                except:
                    pass

            print("=" * 50)

        return response


def get_document_intelligence_client(
    endpoint: Optional[str] = None,
    api_key: Optional[str] = None,
    verbose: bool = False,
) -> DocumentIntelligenceClient:
    """
    Create an Azure Document Intelligence client for analyzing documents.

    Args:
        endpoint: DI endpoint URL (defaults to AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT env var)
        api_key: DI API key (defaults to AZURE_DOCUMENT_INTELLIGENCE_KEY env var)
        verbose: Enable verbose HTTP request/response logging

    Returns:
        DocumentIntelligenceClient instance
    """
    endpoint = endpoint or os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    api_key = api_key or os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_KEY")

    if not endpoint:
        raise ValueError(
            "Document Intelligence endpoint not provided. "
            "Set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT environment variable."
        )
    if not api_key:
        raise ValueError(
            "Document Intelligence API key not provided. "
            "Set AZURE_DOCUMENT_INTELLIGENCE_KEY environment variable."
        )

    # Create custom policy for APIM header
    apim_policy = APIMSubscriptionKeyPolicy(api_key, header_name="api-key", verbose=verbose)

    return DocumentIntelligenceClient(
        endpoint=endpoint,
        credential=AzureKeyCredential("dummy"),  # Dummy credential since we're using custom policy
        per_call_policies=[apim_policy],  # Apply to all initial requests
        per_retry_policies=[apim_policy],  # Apply to all retry/polling requests
    )


def get_document_intelligence_admin_client(
    endpoint: Optional[str] = None,
    api_key: Optional[str] = None,
    verbose: bool = False,
) -> DocumentIntelligenceAdministrationClient:
    """
    Create an Azure Document Intelligence Administration client for managing models.

    Args:
        endpoint: DI endpoint URL (defaults to AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT env var)
        api_key: DI API key (defaults to AZURE_DOCUMENT_INTELLIGENCE_KEY env var)
        verbose: Enable verbose HTTP request/response logging

    Returns:
        DocumentIntelligenceAdministrationClient instance
    """
    endpoint = endpoint or os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    api_key = api_key or os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_KEY")

    if not endpoint:
        raise ValueError(
            "Document Intelligence endpoint not provided. "
            "Set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT environment variable."
        )
    if not api_key:
        raise ValueError(
            "Document Intelligence API key not provided. "
            "Set AZURE_DOCUMENT_INTELLIGENCE_KEY environment variable."
        )

    # Create custom policy for APIM header
    apim_policy = APIMSubscriptionKeyPolicy(api_key, header_name="api-key", verbose=verbose)

    return DocumentIntelligenceAdministrationClient(
        endpoint=endpoint,
        credential=AzureKeyCredential("dummy"),  # Dummy credential since we're using custom policy
        per_call_policies=[apim_policy],  # Apply to all initial requests
        per_retry_policies=[apim_policy],  # Apply to all retry/polling requests
    )

def get_blob_service_client(
    connection_string: Optional[str] = None,
) -> BlobServiceClient:
    """
    Create an Azure Blob Storage service client.

    Args:
        connection_string: Storage connection string
            (defaults to AZURE_STORAGE_CONNECTION_STRING env var)

    Returns:
        BlobServiceClient instance
    """
    connection_string = connection_string or os.environ.get("AZURE_STORAGE_CONNECTION_STRING")

    if not connection_string:
        raise ValueError(
            "Blob Storage connection string not provided. "
            "Set AZURE_STORAGE_CONNECTION_STRING environment variable."
        )

    return BlobServiceClient.from_connection_string(connection_string)


def test_document_intelligence_connection(
    admin_client: Optional[DocumentIntelligenceAdministrationClient] = None,
) -> dict:
    """
    Test Document Intelligence connection by listing models.

    Args:
        admin_client: Optional administration client instance

    Returns:
        Dict with connection status and model count
    """
    if admin_client is None:
        admin_client = get_document_intelligence_admin_client()

    try:
        models = list(admin_client.list_models())
        return {
            "success": True,
            "message": "Connection successful",
            "model_count": len(models),
            "models": [m.model_id for m in models[:10]],  # First 10 models
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Connection failed: {str(e)}",
            "model_count": 0,
            "models": [],
        }


def test_blob_storage_connection(
    client: Optional[BlobServiceClient] = None,
    container_name: Optional[str] = None,
) -> dict:
    """
    Test Blob Storage connection by listing containers.

    Args:
        client: Optional client instance
        container_name: Optional specific container to check

    Returns:
        Dict with connection status
    """
    if client is None:
        client = get_blob_service_client()

    container_name = container_name or os.environ.get("AZURE_STORAGE_CONTAINER_NAME")

    try:
        containers = list(client.list_containers())
        container_names = [c.name for c in containers]

        result = {
            "success": True,
            "message": "Connection successful",
            "container_count": len(containers),
            "containers": container_names,
        }

        if container_name:
            result["target_container_exists"] = container_name in container_names

        return result
    except Exception as e:
        return {
            "success": False,
            "message": f"Connection failed: {str(e)}",
            "container_count": 0,
            "containers": [],
        }
