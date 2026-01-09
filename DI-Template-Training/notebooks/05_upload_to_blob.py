# %% [markdown]
# # 05 - Upload to Azure Blob Storage
#
# This notebook uploads the training data to Azure Blob Storage:
# - Training images (*.jpg)
# - OCR JSON files (*.ocr.json)
# - Label files (*.labels.json)
# - Field schema (fields.json)
#
# After upload, a SAS URL is generated for model training.

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

from src.utils import save_json, load_json
from src.azure_client import get_blob_service_client
from src.blob_storage import (
    ensure_container_exists,
    upload_training_data,
    generate_sas_url,
    list_container_blobs,
    delete_container_contents,
)
from src.labels_generator import validate_training_data

print(f"Project root: {project_root}")

# %% [markdown]
# ## 1. Configuration

# %%
# Paths
DATA_DIR = project_root / "data"
TRAINING_DIR = DATA_DIR / "training"
CONFIG_DIR = project_root / "data" / "outputs"

# Azure configuration
CONTAINER_NAME = os.environ.get("AZURE_STORAGE_CONTAINER_NAME", "di-training-data")

print(f"Training directory: {TRAINING_DIR}")
print(f"Target container: {CONTAINER_NAME}")

# Ensure config directory exists
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# %% [markdown]
# ## 2. Validate Training Data Before Upload

# %%
# Validate training data
validation = validate_training_data(TRAINING_DIR)

print("Pre-upload Validation:")
print("-" * 50)
print(f"Status: {'VALID' if validation['valid'] else 'INVALID'}")
print(f"Images: {validation['image_count']}")

if validation['issues']:
    print("\nIssues found:")
    for issue in validation['issues']:
        print(f"  - {issue}")
    print("\nPlease resolve these issues before uploading.")
else:
    print("\nAll validation checks passed.")

# %%
# List files to upload
print("\nFiles to upload:")
print("-" * 50)

files_to_upload = []

# fields.json
fields_json = TRAINING_DIR / "fields.json"
if fields_json.exists():
    files_to_upload.append(fields_json)
    print(f"  fields.json ({fields_json.stat().st_size / 1024:.1f} KB)")

# Training samples
for img in sorted(TRAINING_DIR.glob("*.jpg")):
    files_to_upload.append(img)
    print(f"  {img.name} ({img.stat().st_size / 1024:.1f} KB)")

    ocr_file = TRAINING_DIR / f"{img.name}.ocr.json"
    if ocr_file.exists():
        files_to_upload.append(ocr_file)
        print(f"    + {ocr_file.name} ({ocr_file.stat().st_size / 1024:.1f} KB)")

    labels_file = TRAINING_DIR / f"{img.name}.labels.json"
    if labels_file.exists():
        files_to_upload.append(labels_file)
        print(f"    + {labels_file.name} ({labels_file.stat().st_size / 1024:.1f} KB)")

total_size = sum(f.stat().st_size for f in files_to_upload) / (1024 * 1024)
print(f"\nTotal: {len(files_to_upload)} files, {total_size:.2f} MB")

# %% [markdown]
# ## 3. Initialize Blob Storage Client

# %%
# Initialize client
blob_client = get_blob_service_client()
print("Blob Storage client initialized.")

# Check/create container
created = ensure_container_exists(blob_client, CONTAINER_NAME)
if created:
    print(f"Created new container: {CONTAINER_NAME}")
else:
    print(f"Container already exists: {CONTAINER_NAME}")

# %% [markdown]
# ## 4. Clear Existing Data (Optional)
#
# Uncomment the cell below if you want to clear existing training data before upload.

# %%
# # OPTIONAL: Clear existing container contents
# print("Clearing existing container contents...")
# deleted = delete_container_contents(blob_client, CONTAINER_NAME, verbose=True)
# print(f"Deleted {deleted} blobs")

# %% [markdown]
# ## 5. Upload Training Data

# %%
# Upload all training data
print(f"\nUploading to container: {CONTAINER_NAME}")
print("-" * 60)

result = upload_training_data(
    client=blob_client,
    container_name=CONTAINER_NAME,
    training_dir=TRAINING_DIR,
    verbose=True,
)

print(f"\nUpload complete!")
print(f"  Total files: {result['total_files']}")
print(f"  Uploaded: {result['uploaded']}")
print(f"  Failed: {result['failed']}")

if result['failed_files']:
    print("\nFailed uploads:")
    for f in result['failed_files']:
        print(f"  - {f['file']}: {f['error']}")

# %% [markdown]
# ## 6. Verify Upload

# %%
# List uploaded blobs
blobs = list_container_blobs(blob_client, CONTAINER_NAME)

print(f"\nBlobs in container '{CONTAINER_NAME}':")
print("-" * 60)

for blob in blobs:
    size_kb = blob['size'] / 1024
    print(f"  {blob['name']:<50} {size_kb:>8.1f} KB")

print(f"\nTotal blobs: {len(blobs)}")

# %% [markdown]
# ## 7. Generate SAS URL

# %%
# Generate SAS URL for training
sas_url = generate_sas_url(
    client=blob_client,
    container_name=CONTAINER_NAME,
    expiry_days=7,  # Valid for 7 days
)

print("SAS URL Generated:")
print("-" * 60)
print(f"URL (first 100 chars): {sas_url[:100]}...")
print(f"\nExpires in: 7 days")

# %%
# Save SAS URL to config file for next notebook
config = {
    "container_name": CONTAINER_NAME,
    "sas_url": sas_url,
    "blob_count": len(blobs),
    "image_count": len([b for b in blobs if b['name'].endswith('.jpg')]),
}

config_path = CONFIG_DIR / "upload_config.json"
save_json(config, config_path)

print(f"\nConfiguration saved to: {config_path}")

# %% [markdown]
# ## 8. Summary

# %%
print("\n" + "=" * 60)
print("UPLOAD SUMMARY")
print("=" * 60)

print(f"\nContainer: {CONTAINER_NAME}")
print(f"Files uploaded: {result['uploaded']}")
print(f"Total size: {sum(b['size'] for b in blobs) / (1024*1024):.2f} MB")

# Check requirements
images = [b for b in blobs if b['name'].endswith('.jpg')]
ocr_files = [b for b in blobs if b['name'].endswith('.ocr.json')]
labels_files = [b for b in blobs if b['name'].endswith('.labels.json')]
has_fields = any(b['name'] == 'fields.json' for b in blobs)

print(f"\nTraining data:")
print(f"  Images: {len(images)}")
print(f"  OCR files: {len(ocr_files)}")
print(f"  Label files: {len(labels_files)}")
print(f"  fields.json: {'YES' if has_fields else 'NO'}")

# Validate completeness
complete = (
    len(images) >= 5 and
    len(ocr_files) == len(images) and
    len(labels_files) == len(images) and
    has_fields
)

if complete:
    print("\nTraining data upload COMPLETE!")
    print("\nYou can proceed to the next notebook: 06_train_model.py")
else:
    print("\nWARNING: Training data may be incomplete.")
    print("Please verify all required files are uploaded.")

# %%
