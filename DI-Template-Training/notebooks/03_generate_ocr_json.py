# %% [markdown]
# # 03 - Generate OCR JSON Files
#
# This notebook generates `.ocr.json` files for each aligned training image
# using Azure Document Intelligence Layout API.
#
# The OCR output contains:
# - All detected words with positions
# - Page dimensions
# - Text spans and confidence scores
#
# These files are required for Azure DI custom model training.

# %%
# Standard imports
import os
import sys
import json
from pathlib import Path

import matplotlib.pyplot as plt

# Add project root to path
project_root = Path.cwd().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from src.utils import load_json, ensure_dir
from src.azure_client import get_document_intelligence_client
from src.ocr_generator import (
    generate_ocr_json,
    generate_ocr_json_batch,
    extract_words_from_ocr,
    get_page_dimensions,
)

print(f"Project root: {project_root}")

# %% [markdown]
# ## 1. Configuration

# %%
# Paths
DATA_DIR = project_root / "data"
ALIGNED_DIR = DATA_DIR / "aligned"
TRAINING_DIR = DATA_DIR / "training"

# Ensure training directory exists
ensure_dir(TRAINING_DIR)

print(f"Aligned images: {ALIGNED_DIR}")
print(f"Training output: {TRAINING_DIR}")

# List aligned images
aligned_files = sorted(ALIGNED_DIR.glob("*.jpg"))
print(f"\nFound {len(aligned_files)} aligned images:")
for f in aligned_files:
    print(f"  - {f.name}")

# %% [markdown]
# ## 2. Initialize Azure Document Intelligence Client

# %%
# Initialize client
di_client = get_document_intelligence_client()
print("Document Intelligence client initialized.")

# Show endpoint (masked)
endpoint = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", "")
print(f"Endpoint: {endpoint[:30]}...")

# %% [markdown]
# ## 3. Copy Aligned Images to Training Directory

# %%
import shutil

# Copy aligned images to training directory
copied = 0
for img_path in aligned_files:
    dst_path = TRAINING_DIR / img_path.name
    if not dst_path.exists():
        shutil.copy(img_path, dst_path)
        copied += 1

print(f"Copied {copied} images to training directory")
print(f"Training directory now has {len(list(TRAINING_DIR.glob('*.jpg')))} images")

# %% [markdown]
# ## 4. Process Single Image (Demo)
#
# First, let's process one image to see the OCR output structure.

# %%
# Process first image as demo
if aligned_files:
    demo_image = aligned_files[0]
    demo_output = TRAINING_DIR / f"{demo_image.name}.ocr.json"

    print(f"Processing: {demo_image.name}")
    print("This may take 10-30 seconds...")

    ocr_data = generate_ocr_json(di_client, demo_image, demo_output)

    print(f"\nOCR JSON saved to: {demo_output}")

# %%
# Inspect OCR output structure
if 'ocr_data' in dir():
    print("OCR JSON Structure:")
    print("-" * 50)

    analyze_result = ocr_data.get("analyzeResult", ocr_data)

    print(f"API Version: {analyze_result.get('apiVersion', 'N/A')}")
    print(f"Model ID: {analyze_result.get('modelId', 'N/A')}")

    pages = analyze_result.get("pages", [])
    print(f"Pages: {len(pages)}")

    if pages:
        page = pages[0]
        print(f"\nPage 1:")
        print(f"  Dimensions: {page.get('width')} x {page.get('height')} {page.get('unit', 'pixel')}")
        print(f"  Words: {len(page.get('words', []))}")
        print(f"  Lines: {len(page.get('lines', []))}")

# %%
# Show sample words
if 'ocr_data' in dir():
    words = extract_words_from_ocr(ocr_data)

    print(f"\nExtracted {len(words)} words")
    print("\nSample words (first 10):")
    print("-" * 70)
    print(f"{'Text':<30} {'Confidence':<12} {'Position (x, y)'}")
    print("-" * 70)

    for word in words[:10]:
        bbox = word.get("bbox", {})
        pos = f"({bbox.get('x', 0):.0f}, {bbox.get('y', 0):.0f})"
        print(f"{word['text']:<30} {word['confidence']:.3f}       {pos}")

# %% [markdown]
# ## 5. Batch Process All Images
#
# Now process all remaining aligned images.

# %%
# Get images that need OCR processing
training_images = sorted(TRAINING_DIR.glob("*.jpg"))
images_to_process = [
    img for img in training_images
    if not (TRAINING_DIR / f"{img.name}.ocr.json").exists()
]

print(f"Images to process: {len(images_to_process)}")
print(f"Already processed: {len(training_images) - len(images_to_process)}")

# %%
# Process remaining images
if images_to_process:
    print(f"\nProcessing {len(images_to_process)} images...")
    print("This may take several minutes depending on the number of images.")
    print("-" * 60)

    results = generate_ocr_json_batch(
        di_client,
        images_to_process,
        output_dir=TRAINING_DIR,
        verbose=True,
    )

    # Summary
    successful = sum(1 for r in results if r.get("success"))
    print(f"\nProcessed: {successful}/{len(results)} images successfully")

    # Show any failures
    failures = [r for r in results if not r.get("success")]
    if failures:
        print("\nFailed images:")
        for f in failures:
            print(f"  - {f['image']}: {f.get('error', 'Unknown error')}")
else:
    print("All images already have OCR JSON files.")

# %% [markdown]
# ## 6. Verify OCR Output

# %%
# List all OCR JSON files
ocr_files = sorted(TRAINING_DIR.glob("*.ocr.json"))

print(f"\nOCR JSON Files Generated: {len(ocr_files)}")
print("-" * 60)

for ocr_file in ocr_files:
    # Load and check file
    data = load_json(ocr_file)
    words = extract_words_from_ocr(data)
    width, height = get_page_dimensions(data)

    img_name = ocr_file.name.replace(".ocr.json", "")
    print(f"  {img_name}: {len(words)} words, {width}x{height}px")

# %% [markdown]
# ## 7. Summary

# %%
print("\n" + "=" * 60)
print("OCR GENERATION SUMMARY")
print("=" * 60)

training_images = list(TRAINING_DIR.glob("*.jpg"))
ocr_files = list(TRAINING_DIR.glob("*.ocr.json"))

print(f"\nTraining images: {len(training_images)}")
print(f"OCR JSON files: {len(ocr_files)}")

# Check completeness
missing_ocr = [
    img.name for img in training_images
    if not (TRAINING_DIR / f"{img.name}.ocr.json").exists()
]

if missing_ocr:
    print(f"\nWARNING: {len(missing_ocr)} images missing OCR files:")
    for name in missing_ocr:
        print(f"  - {name}")
else:
    print("\nAll images have OCR JSON files.")
    print("\nYou can proceed to the next notebook: 04_generate_labels.py")

# %%
