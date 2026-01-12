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
# Set verbose=True to enable detailed HTTP request/response logging for debugging
VERBOSE = True  # Set to True if you need to debug API calls
di_client = get_document_intelligence_client(verbose=VERBOSE)
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
DOCUMENT_INDEX = 5

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

    try:
        # Read document
        with open(test_document, "rb") as f:
            document_data = f.read()

        print(f"Document size: {len(document_data)} bytes")

        # Analyze with custom model using manual polling
        # The Azure SDK's built-in poller doesn't work correctly with APIM gateway
        import requests
        import time

        print(f"\nSubmitting document to model: {MODEL_ID}")

        # Get endpoint and API key from environment
        endpoint = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        api_key = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_KEY")

        # Submit document for analysis
        analyze_url = f"{endpoint}/documentintelligence/documentModels/{MODEL_ID}:analyze?api-version=2024-11-30"

        headers = {
            "api-key": api_key,
            "Content-Type": "application/octet-stream",
        }

        print(f"POST {analyze_url}")
        response = requests.post(analyze_url, headers=headers, data=document_data)
        print(f"Response status: {response.status_code}")

        if response.status_code != 202:
            print(f"ERROR: Expected 202 Accepted, got {response.status_code}")
            print(f"Response: {response.text}")
            result = None
        else:
            # Get the operation location for polling
            operation_location = response.headers.get("Operation-Location")
            print(f"Operation-Location: {operation_location}")

            # Poll until complete
            print("\nPolling for results...")
            poll_headers = {"api-key": api_key}
            max_attempts = 60  # 60 attempts * 2 seconds = 2 minutes max
            attempt = 0

            while attempt < max_attempts:
                attempt += 1
                time.sleep(2)  # Wait 2 seconds between polls

                poll_response = requests.get(operation_location, headers=poll_headers)
                poll_data = poll_response.json()

                status = poll_data.get("status", "unknown")
                print(f"  Attempt {attempt}: status = {status}")

                if status == "succeeded":
                    print("Analysis succeeded!")
                    # Parse the result into the expected format
                    # The polling response contains the full result
                    import json
                    from azure.ai.documentintelligence.models import AnalyzeResult

                    # Use the Azure SDK's internal deserialization
                    analyze_result_data = poll_data.get("analyzeResult", {})

                    # Create AnalyzeResult from the JSON response
                    # The SDK uses a deserializer, but we can use the model constructor
                    result = AnalyzeResult._from_generated(analyze_result_data) if hasattr(AnalyzeResult, '_from_generated') else None

                    # If that doesn't work, try direct instantiation
                    if result is None:
                        # Store the raw result and we'll handle it manually
                        result = type('AnalyzeResult', (), {
                            'documents': [],
                            'pages': [],
                            'tables': [],
                            'key_value_pairs': [],
                            'model_id': poll_data.get('modelId'),
                            '_raw_data': poll_data
                        })()

                        # Parse documents
                        for doc_data in analyze_result_data.get('documents', []):
                            doc = type('Document', (), {
                                'doc_type': doc_data.get('docType'),
                                'fields': {},
                                'confidence': doc_data.get('confidence', 1.0),
                                'bounding_regions': doc_data.get('boundingRegions', [])
                            })()

                            # Parse fields
                            for field_name, field_data in doc_data.get('fields', {}).items():
                                field = type('DocumentField', (), {
                                    'value': field_data.get('content') or field_data.get('valueString') or field_data.get('valueNumber'),
                                    'content': field_data.get('content'),
                                    'confidence': field_data.get('confidence', 0.0),
                                    'bounding_regions': field_data.get('boundingRegions', [])
                                })()
                                doc.fields[field_name] = field

                            result.documents.append(doc)

                    break
                elif status == "failed":
                    print(f"Analysis failed: {poll_data}")
                    result = None
                    break
            else:
                print("ERROR: Polling timed out after 2 minutes")
                result = None

        # Check if result is valid
        if result is None:
            print("ERROR: Analysis returned None. Check your model ID and API configuration.")
            print(f"Model ID used: {MODEL_ID}")
        else:
            print("Analysis complete!")
            print(f"Number of documents: {len(result.documents) if hasattr(result, 'documents') else 0}")
    except Exception as e:
        print(f"ERROR during analysis: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print(f"Model ID used: {MODEL_ID}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
        result = None

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
if 'result' in dir() and result is not None:
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
if 'result' in dir() and result is not None and test_document:
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
