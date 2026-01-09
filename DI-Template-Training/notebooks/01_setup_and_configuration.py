# %% [markdown]
# # 01 - Setup and Configuration
#
# This notebook verifies your Azure environment is properly configured:
# - Azure Document Intelligence connection
# - Azure Blob Storage connection
# - Required paths and directories
#
# **Prerequisites:**
# 1. Copy `sample.env` to `.env` and fill in your Azure credentials
# 2. Run `poetry install` to install dependencies

# %%
# Standard imports
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path.cwd().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

print(f"Project root: {project_root}")

# %% [markdown]
# ## 1. Check Environment Variables

# %%
# Check required environment variables
required_vars = [
    "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT",
    "AZURE_DOCUMENT_INTELLIGENCE_KEY",
    "AZURE_STORAGE_CONNECTION_STRING",
    "AZURE_STORAGE_CONTAINER_NAME",
]

print("Environment Variable Status:")
print("-" * 50)

all_set = True
for var in required_vars:
    value = os.environ.get(var)
    if value:
        # Show masked value
        masked = value[:10] + "..." if len(value) > 10 else value
        print(f"  {var}: {masked}")
    else:
        print(f"  {var}: NOT SET")
        all_set = False

if all_set:
    print("\nAll required environment variables are set.")
else:
    print("\nWARNING: Some environment variables are missing!")
    print("Please update your .env file.")

# %% [markdown]
# ## 2. Test Azure Document Intelligence Connection

# %%
from src.azure_client import (
    get_document_intelligence_client,
    test_document_intelligence_connection,
)

# Initialize client
try:
    di_client = get_document_intelligence_client()
    print("Document Intelligence client initialized successfully.")
except Exception as e:
    print(f"Failed to initialize client: {e}")
    di_client = None

# %%
# Test connection
if di_client:
    result = test_document_intelligence_connection(di_client)

    print("\nDocument Intelligence Connection Test:")
    print("-" * 50)
    print(f"  Status: {'SUCCESS' if result['success'] else 'FAILED'}")
    print(f"  Message: {result['message']}")

    if result['success']:
        print(f"  Custom Models: {result['model_count']}")
        if result['models']:
            print("  Recent models:")
            for model in result['models'][:5]:
                print(f"    - {model}")

# %% [markdown]
# ## 3. Test Azure Blob Storage Connection

# %%
from src.azure_client import (
    get_blob_service_client,
    test_blob_storage_connection,
)

# Initialize client
try:
    blob_client = get_blob_service_client()
    print("Blob Storage client initialized successfully.")
except Exception as e:
    print(f"Failed to initialize client: {e}")
    blob_client = None

# %%
# Test connection
if blob_client:
    container_name = os.environ.get("AZURE_STORAGE_CONTAINER_NAME", "di-training-data")
    result = test_blob_storage_connection(blob_client, container_name)

    print("\nBlob Storage Connection Test:")
    print("-" * 50)
    print(f"  Status: {'SUCCESS' if result['success'] else 'FAILED'}")
    print(f"  Message: {result['message']}")

    if result['success']:
        print(f"  Containers: {result['container_count']}")
        if "target_container_exists" in result:
            exists = result['target_container_exists']
            print(f"  Target container '{container_name}': {'EXISTS' if exists else 'DOES NOT EXIST'}")
            if not exists:
                print("  (Container will be created during upload)")

# %% [markdown]
# ## 4. Verify Template-alignment Integration

# %%
from src.alignment_wrapper import get_template_paths

try:
    paths = get_template_paths()

    print("\nTemplate-alignment Integration:")
    print("-" * 50)

    for name, path in paths.items():
        exists = path.exists()
        status = "OK" if exists else "MISSING"
        print(f"  {name}: {status}")
        if exists:
            if path.is_dir():
                file_count = len(list(path.iterdir()))
                print(f"    -> {path} ({file_count} files)")
            else:
                print(f"    -> {path}")

except Exception as e:
    print(f"\nTemplate-alignment integration error: {e}")
    print("Make sure TEMPLATE_ALIGNMENT_PATH is set correctly in .env")

# %% [markdown]
# ## 5. Verify Local Directory Structure

# %%
# Check local directories
local_dirs = [
    project_root / "data" / "inputs" / "sample_forms",
    project_root / "data" / "aligned",
    project_root / "data" / "training",
    project_root / "data" / "outputs",
    project_root / "templates",
]

print("\nLocal Directory Structure:")
print("-" * 50)

for dir_path in local_dirs:
    exists = dir_path.exists()
    status = "OK" if exists else "MISSING"
    print(f"  {dir_path.relative_to(project_root)}: {status}")

    if not exists:
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"    -> Created")

# %% [markdown]
# ## 6. Configuration Summary

# %%
print("\n" + "=" * 60)
print("CONFIGURATION SUMMARY")
print("=" * 60)

# Document Intelligence
di_ok = di_client is not None and result.get('success', False) if 'result' in dir() else False
print(f"\nDocument Intelligence: {'READY' if di_ok else 'NOT READY'}")

# Blob Storage
blob_ok = blob_client is not None
print(f"Blob Storage: {'READY' if blob_ok else 'NOT READY'}")

# Template-alignment
try:
    paths = get_template_paths()
    ta_ok = all(p.exists() for p in paths.values())
except:
    ta_ok = False
print(f"Template-alignment: {'READY' if ta_ok else 'NOT READY'}")

# Overall
all_ready = di_ok and blob_ok and ta_ok
print(f"\nOverall Status: {'ALL SYSTEMS READY' if all_ready else 'SETUP INCOMPLETE'}")

if all_ready:
    print("\nYou can proceed to the next notebook: 02_prepare_training_data.py")
else:
    print("\nPlease resolve the issues above before proceeding.")

# %%
