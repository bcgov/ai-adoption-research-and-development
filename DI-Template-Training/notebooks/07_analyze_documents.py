# %% [markdown]
# # 07 - Analyze Documents
#
# This notebook demonstrates how to use the trained custom model
# to analyze new documents and extract fields.
#
# Features:
# - Analyze from local file or URL
# - Parse and display extracted fields
# - Visualize extraction on document image
# - Export results to JSON

# %%
# Standard imports
import os
import sys
from pathlib import Path

import cv2
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# Add project root to path
project_root = Path.cwd().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from src.utils import load_json, save_json, load_image
from src.azure_client import get_document_intelligence_client

print(f"Project root: {project_root}")

# %% [markdown]
# ## 1. Configuration

# %%
# Paths
DATA_DIR = project_root / "data"
CONFIG_DIR = DATA_DIR / "outputs"
INPUTS_DIR = DATA_DIR / "inputs" / "sample_forms"
OUTPUTS_DIR = DATA_DIR / "outputs"

# Ensure output directory exists
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

print(f"Input directory: {INPUTS_DIR}")
print(f"Output directory: {OUTPUTS_DIR}")

# %% [markdown]
# ## 2. Load Model Configuration

# %%
# Load model config from training step
model_config_path = CONFIG_DIR / "model_config.json"

if model_config_path.exists():
    model_config = load_json(model_config_path)
    MODEL_ID = model_config.get("model_id")
    print(f"Loaded model configuration:")
    print(f"  Model ID: {MODEL_ID}")
    print(f"  Created: {model_config.get('created', 'Unknown')}")
    if "fields" in model_config:
        print(f"  Fields: {len(model_config['fields'])}")
else:
    # Fallback to environment variable
    MODEL_ID = os.environ.get("DI_MODEL_ID", "custom-template-model")
    print(f"Using model ID from environment: {MODEL_ID}")

# %% [markdown]
# ## 3. Initialize Client

# %%
# Initialize Document Intelligence client
di_client = get_document_intelligence_client()
print("Document Intelligence client initialized.")

# %% [markdown]
# ## 4. Select Test Document

# %%
# List available input documents
input_files = sorted(INPUTS_DIR.glob("*.jpg"))

print(f"Available test documents ({len(input_files)}):")
for i, f in enumerate(input_files):
    print(f"  [{i}] {f.name}")

# %%
# Select a document to analyze
# Change this index to test different documents
DOCUMENT_INDEX = 0

if input_files:
    test_document = input_files[DOCUMENT_INDEX]
    print(f"\nSelected document: {test_document.name}")
else:
    print("No input documents found!")
    test_document = None

# %% [markdown]
# ## 5. Analyze Document

# %%
if test_document:
    print(f"Analyzing: {test_document.name}")
    print("This may take 10-30 seconds...")
    print("-" * 50)

    # Read document
    with open(test_document, "rb") as f:
        document_data = f.read()

    # Analyze with custom model
    poller = di_client.begin_analyze_document(
        model_id=MODEL_ID,
        body=document_data,
        content_type="application/octet-stream",
    )

    # Wait for result
    result = poller.result()
    print("Analysis complete!")

# %% [markdown]
# ## 6. Parse Extraction Results

# %%
def parse_field_value(field):
    """Extract value from a field object."""
    if field is None:
        return None

    # Handle different value types
    if hasattr(field, 'value'):
        return field.value
    if hasattr(field, 'content'):
        return field.content
    if hasattr(field, 'value_string'):
        return field.value_string
    if hasattr(field, 'value_number'):
        return field.value_number
    if hasattr(field, 'value_date'):
        return str(field.value_date)
    if hasattr(field, 'value_selection_mark'):
        return field.value_selection_mark

    return str(field)


def get_field_confidence(field):
    """Get confidence score for a field."""
    if field is None:
        return 0.0
    return getattr(field, 'confidence', 0.0)


def get_field_bounding_regions(field):
    """Get bounding regions for a field."""
    if field is None:
        return []
    regions = getattr(field, 'bounding_regions', [])
    return regions if regions else []

# %%
if 'result' in dir():
    print("\nExtracted Fields:")
    print("=" * 70)
    print(f"{'Field Name':<35} {'Value':<25} {'Confidence'}")
    print("-" * 70)

    extracted_data = {}

    if result.documents:
        for doc in result.documents:
            if doc.fields:
                for field_name, field in doc.fields.items():
                    value = parse_field_value(field)
                    confidence = get_field_confidence(field)

                    # Store in dict
                    extracted_data[field_name] = {
                        "value": value,
                        "confidence": confidence,
                    }

                    # Display
                    value_str = str(value)[:25] if value else "N/A"
                    conf_str = f"{confidence:.2%}" if confidence else "N/A"
                    print(f"{field_name:<35} {value_str:<25} {conf_str}")

    print("-" * 70)
    print(f"Total fields extracted: {len(extracted_data)}")

# %% [markdown]
# ## 7. Visualize Extraction

# %%
if 'result' in dir() and test_document:
    # Load document image
    image = load_image(test_document)
    height, width = image.shape[:2]

    fig, ax = plt.subplots(figsize=(12, 15))
    ax.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

    # Colors for different confidence levels
    def get_color(confidence):
        if confidence >= 0.8:
            return 'green'
        elif confidence >= 0.5:
            return 'orange'
        else:
            return 'red'

    # Draw bounding boxes
    if result.documents:
        for doc in result.documents:
            if doc.fields:
                for field_name, field in doc.fields.items():
                    regions = get_field_bounding_regions(field)
                    confidence = get_field_confidence(field)
                    color = get_color(confidence)

                    for region in regions:
                        if hasattr(region, 'polygon') and region.polygon:
                            polygon = region.polygon
                            # Convert to pixel coordinates
                            points = [(p.x * width, p.y * height) for p in polygon]
                            if points:
                                xs = [p[0] for p in points]
                                ys = [p[1] for p in points]
                                rect = Rectangle(
                                    (min(xs), min(ys)),
                                    max(xs) - min(xs),
                                    max(ys) - min(ys),
                                    linewidth=2,
                                    edgecolor=color,
                                    facecolor='none',
                                    alpha=0.7,
                                )
                                ax.add_patch(rect)
                                ax.text(
                                    min(xs), min(ys) - 5,
                                    f"{field_name[:15]}",
                                    fontsize=6,
                                    color=color,
                                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.7),
                                )

    ax.set_title(
        f"Extraction Results: {test_document.name}\n"
        "(Green: High Conf, Orange: Medium, Red: Low)",
        fontsize=12,
    )
    ax.axis('off')
    plt.tight_layout()
    plt.show()

# %% [markdown]
# ## 8. Export Results

# %%
if 'extracted_data' in dir() and test_document:
    # Save extraction results
    output_path = OUTPUTS_DIR / f"{test_document.stem}_extraction.json"

    output_data = {
        "document": test_document.name,
        "model_id": MODEL_ID,
        "fields": extracted_data,
    }

    save_json(output_data, output_path)
    print(f"Results saved to: {output_path}")

# %% [markdown]
# ## 9. Display Summary Table

# %%
if 'extracted_data' in dir():
    print("\n" + "=" * 60)
    print("EXTRACTION SUMMARY")
    print("=" * 60)

    # Categorize fields
    high_conf = [f for f, d in extracted_data.items() if d['confidence'] >= 0.8]
    medium_conf = [f for f, d in extracted_data.items() if 0.5 <= d['confidence'] < 0.8]
    low_conf = [f for f, d in extracted_data.items() if d['confidence'] < 0.5]

    print(f"\nHigh confidence (>= 80%): {len(high_conf)} fields")
    print(f"Medium confidence (50-80%): {len(medium_conf)} fields")
    print(f"Low confidence (< 50%): {len(low_conf)} fields")

    if low_conf:
        print("\nLow confidence fields:")
        for field in low_conf:
            print(f"  - {field}: {extracted_data[field]['confidence']:.2%}")

    print("\nExtraction complete!")
    print("\nFor batch processing, proceed to: 08_batch_analysis.py")

# %%
