# %% [markdown]
# # 06 - Train Custom Template Model
#
# This notebook trains a custom template model using Azure Document Intelligence.
#
# The training process:
# 1. Loads configuration from previous upload step
# 2. Submits build request with `buildMode: "template"`
# 3. Polls for completion (typically 1-5 minutes)
# 4. Saves model details for analysis

# %%
# Standard imports
import os
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path.cwd().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from src.utils import load_json, save_json
from src.azure_client import get_document_intelligence_admin_client

print(f"Project root: {project_root}")

# %% [markdown]
# ## 1. Configuration

# %%
# Paths
CONFIG_DIR = project_root / "data" / "outputs"

# Model configuration
MODEL_ID = os.environ.get("DI_MODEL_ID", "custom-template-model")
MODEL_DESCRIPTION = os.environ.get(
    "DI_MODEL_DESCRIPTION",
    "Custom template model for form extraction"
)

print(f"Model ID: {MODEL_ID}")
print(f"Description: {MODEL_DESCRIPTION}")

# %% [markdown]
# ## 2. Load Upload Configuration

# %%
# Load SAS URL from previous step
upload_config_path = CONFIG_DIR / "upload_config.json"

if upload_config_path.exists():
    upload_config = load_json(upload_config_path)
    SAS_URL = upload_config.get("sas_url")
    CONTAINER_NAME = upload_config.get("container_name")
    IMAGE_COUNT = upload_config.get("image_count", 0)

    print("Upload configuration loaded:")
    print(f"  Container: {CONTAINER_NAME}")
    print(f"  Images: {IMAGE_COUNT}")
    print(f"  SAS URL: {SAS_URL[:80]}...")
else:
    print("ERROR: Upload configuration not found!")
    print("Please run notebook 05_upload_to_blob.py first.")
    SAS_URL = None

# %% [markdown]
# ## 3. Initialize Document Intelligence Admin Client

# %%
# Initialize admin client (for model management)
di_admin_client = get_document_intelligence_admin_client()
print("Document Intelligence admin client initialized.")

# Show endpoint
endpoint = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", "")
print(f"Endpoint: {endpoint}")

# %% [markdown]
# ## 4. Check Existing Models

# %%
# List existing custom models
models = list(di_admin_client.list_models())

print(f"Existing custom models: {len(models)}")
print("-" * 50)

for model in models[:10]:
    print(f"  {model.model_id}")
    if hasattr(model, 'created_date_time'):
        print(f"    Created: {model.created_date_time}")

# Check if our model already exists
existing_model = None
for model in models:
    if model.model_id == MODEL_ID:
        existing_model = model
        break

if existing_model:
    print(f"\nWARNING: Model '{MODEL_ID}' already exists!")
    print("Training will create a new version or fail if names conflict.")

# %% [markdown]
# ## 5. Start Model Training

# %%
from azure.ai.documentintelligence.models import (
    BuildDocumentModelRequest,
    AzureBlobContentSource,
)

if SAS_URL:
    print(f"Starting model training...")
    print(f"  Model ID: {MODEL_ID}")
    print(f"  Build mode: template")
    print("-" * 50)

    # Build request
    request = BuildDocumentModelRequest(
        model_id=MODEL_ID,
        description=MODEL_DESCRIPTION,
        build_mode="template",
        azure_blob_source=AzureBlobContentSource(
            container_url=SAS_URL,
        ),
    )

    # Start training
    print("\n[DEBUG] Calling begin_build_document_model...")
    print(f"[DEBUG] Endpoint: {di_admin_client._client._base_url}")
    print(f"[DEBUG] Model ID: {MODEL_ID}")

    poller = di_admin_client.begin_build_document_model(request)

    print("\n[DEBUG] Training request submitted successfully")
    print(f"[DEBUG] Poller status: {poller.status()}")

    # Extract polling URL from the poller
    if hasattr(poller, '_polling_method'):
        polling_method = poller._polling_method
        if hasattr(polling_method, '_pipeline_response'):
            pipeline_response = polling_method._pipeline_response
            if hasattr(pipeline_response, 'http_response'):
                http_response = pipeline_response.http_response
                print(f"[DEBUG] Initial response status: {http_response.status_code}")
                print(f"[DEBUG] Initial response URL: {http_response.request.url}")

                # Check for Operation-Location header (polling URL)
                if hasattr(http_response, 'headers'):
                    headers = http_response.headers
                    for header_name in ['Operation-Location', 'operation-location', 'Location', 'location']:
                        if header_name in headers:
                            print(f"[DEBUG] {header_name} header: {headers[header_name]}")

    print("\nTraining started. This may take 1-5 minutes...")

# %% [markdown]
# ## 6. Monitor Training Progress

# %%
if 'poller' in dir():
    # Poll for completion
    print("Waiting for training to complete...")
    print("-" * 50)

    start_time = time.time()
    last_status = None

    # Show polling URL once
    polling_url_shown = False

    while not poller.done():
        status = poller.status()

        # Show polling URL on first iteration
        if not polling_url_shown and hasattr(poller, '_polling_method'):
            polling_method = poller._polling_method
            if hasattr(polling_method, '_pipeline_response'):
                pipeline_response = polling_method._pipeline_response
                if hasattr(pipeline_response, 'http_response'):
                    http_response = pipeline_response.http_response
                    print(f"[DEBUG] Polling URL: {http_response.request.url}")
                    print(f"[DEBUG] Polling method: {http_response.request.method}")
            polling_url_shown = True

        if status != last_status:
            elapsed = time.time() - start_time
            print(f"  [{elapsed:.0f}s] Status: {status}")
            last_status = status
        time.sleep(5)

    elapsed = time.time() - start_time
    print(f"\nTraining completed in {elapsed:.1f} seconds")

    # Get result
    print("\n[DEBUG] Calling poller.result() to get final model...")
    try:
        model = poller.result()
        print("[DEBUG] Successfully retrieved model result")
    except Exception as e:
        print(f"\n[DEBUG] ERROR during poller.result():")
        print(f"[DEBUG] Error type: {type(e).__name__}")
        print(f"[DEBUG] Error message: {str(e)}")

        # Try to get the failing URL from the exception
        if hasattr(e, 'response'):
            response = e.response
            print(f"[DEBUG] Failed response status: {response.status_code if hasattr(response, 'status_code') else 'N/A'}")
            print(f"[DEBUG] Failed request URL: {response.request.url if hasattr(response, 'request') else 'N/A'}")
            print(f"[DEBUG] Failed request method: {response.request.method if hasattr(response, 'request') else 'N/A'}")

        # Also check polling method for the URL
        if hasattr(poller, '_polling_method'):
            polling_method = poller._polling_method
            if hasattr(polling_method, '_pipeline_response'):
                pipeline_response = polling_method._pipeline_response
                if hasattr(pipeline_response, 'http_response'):
                    http_response = pipeline_response.http_response
                    print(f"[DEBUG] Last polling URL: {http_response.request.url}")
                    print(f"[DEBUG] Last polling status: {http_response.status_code}")

        raise  # Re-raise the exception

# %% [markdown]
# ## 7. Display Model Details

# %%
if 'model' in dir():
    print("\n" + "=" * 60)
    print("TRAINED MODEL DETAILS")
    print("=" * 60)

    print(f"\nModel ID: {model.model_id}")
    print(f"Description: {model.description}")
    print(f"Created: {model.created_date_time}")

    if hasattr(model, 'doc_types') and model.doc_types:
        print(f"\nDocument Types:")
        for doc_type, info in model.doc_types.items():
            print(f"  {doc_type}:")
            if hasattr(info, 'field_schema') and info.field_schema:
                print(f"    Fields: {len(info.field_schema)}")
                for field_name, field_info in list(info.field_schema.items())[:10]:
                    field_type = field_info.type if hasattr(field_info, 'type') else 'unknown'
                    print(f"      - {field_name}: {field_type}")
                if len(info.field_schema) > 10:
                    print(f"      ... and {len(info.field_schema) - 10} more fields")

# %% [markdown]
# ## 8. Save Model Configuration

# %%
if 'model' in dir():
    # Save model config for analysis notebooks
    model_config = {
        "model_id": model.model_id,
        "description": model.description,
        "created": str(model.created_date_time),
        "endpoint": os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"),
    }

    # Add field info if available
    if hasattr(model, 'doc_types') and model.doc_types:
        for doc_type, info in model.doc_types.items():
            if hasattr(info, 'field_schema') and info.field_schema:
                model_config["fields"] = list(info.field_schema.keys())
                break

    config_path = CONFIG_DIR / "model_config.json"
    save_json(model_config, config_path)

    print(f"\nModel configuration saved to: {config_path}")

# %% [markdown]
# ## 9. Summary

# %%
print("\n" + "=" * 60)
print("TRAINING SUMMARY")
print("=" * 60)

if 'model' in dir():
    print(f"\nModel '{model.model_id}' trained successfully!")
    print(f"\nYou can now use this model to analyze documents.")
    print("\nNext steps:")
    print("  1. Run 07_analyze_documents.py to test with single documents")
    print("  2. Run 08_batch_analysis.py for batch processing")
else:
    print("\nTraining was not completed.")
    print("Please check the error messages above and try again.")

# %%
