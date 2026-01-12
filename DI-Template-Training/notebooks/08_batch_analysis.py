# %% [markdown]
# # 08 - Batch Analysis
#
# This notebook processes multiple documents using the trained model:
# - Batch extraction with progress tracking
# - Aggregated results in DataFrame/CSV
# - Summary statistics
# - Optional accuracy evaluation (if ground truth available)

# %%
# Standard imports
import os
import sys
import time
from pathlib import Path

import pandas as pd

# Add project root to path
project_root = Path.cwd().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from src.utils import load_json, save_json
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

# Rate limiting (Azure has quotas)
# Note: Polling is done internally in analyze_document, so this is just a small delay between submissions
DELAY_BETWEEN_REQUESTS = 0.5  # seconds

# Ensure output directory exists
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

print(f"Input directory: {INPUTS_DIR}")
print(f"Output directory: {OUTPUTS_DIR}")

# %% [markdown]
# ## 2. Load Model Configuration

# %%
# Load model config
model_config_path = CONFIG_DIR / "model_config.json"

if model_config_path.exists():
    model_config = load_json(model_config_path)
    MODEL_ID = model_config.get("model_id")
    print(f"Model ID: {MODEL_ID}")
else:
    MODEL_ID = os.environ.get("DI_MODEL_ID", "custom-template-model")
    print(f"Using model ID from environment: {MODEL_ID}")

# %% [markdown]
# ## 3. Initialize Client

# %%
# Initialize Document Intelligence client
# Set verbose=True to enable detailed HTTP request/response logging for debugging
VERBOSE = False  # Set to True if you need to debug API calls
di_client = get_document_intelligence_client(verbose=VERBOSE)
print("Document Intelligence client initialized.")

# %% [markdown]
# ## 4. List Documents to Process

# %%
# Get all input documents
input_files = sorted(INPUTS_DIR.glob("*.jpg"))

print(f"Documents to process: {len(input_files)}")
print("-" * 50)

for f in input_files:
    size_kb = f.stat().st_size / 1024
    print(f"  {f.name} ({size_kb:.1f} KB)")

# %% [markdown]
# ## 5. Batch Analysis Function

# %%
def analyze_document(model_id: str, document_path: Path) -> dict:
    """
    Analyze a single document and return extracted fields using manual polling.

    Args:
        model_id: Custom model ID
        document_path: Path to document

    Returns:
        Dict with extracted fields and metadata
    """
    import requests
    import time

    result_data = {
        "document": document_path.name,
        "success": False,
        "error": None,
        "fields": {},
    }

    try:
        with open(document_path, "rb") as f:
            document_data = f.read()

        # Get endpoint and API key from environment
        endpoint = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        api_key = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_KEY")

        # Submit document for analysis
        analyze_url = f"{endpoint}/documentintelligence/documentModels/{model_id}:analyze?api-version=2024-11-30"

        headers = {
            "api-key": api_key,
            "Content-Type": "application/octet-stream",
        }

        response = requests.post(analyze_url, headers=headers, data=document_data)

        if response.status_code != 202:
            result_data["error"] = f"HTTP {response.status_code}: {response.text}"
            return result_data

        # Get the operation location for polling
        operation_location = response.headers.get("Operation-Location")
        if not operation_location:
            result_data["error"] = "No Operation-Location header in response"
            return result_data

        # Poll until complete
        poll_headers = {"api-key": api_key}
        max_attempts = 60  # 60 attempts * 2 seconds = 2 minutes max
        attempt = 0

        while attempt < max_attempts:
            attempt += 1
            time.sleep(2)  # Wait 2 seconds between polls

            poll_response = requests.get(operation_location, headers=poll_headers)
            poll_data = poll_response.json()

            status = poll_data.get("status", "unknown")

            if status == "succeeded":
                # Parse the result
                analyze_result_data = poll_data.get("analyzeResult", {})

                # Parse documents
                for doc_data in analyze_result_data.get('documents', []):
                    # Parse fields
                    for field_name, field_data in doc_data.get('fields', {}).items():
                        # Extract value based on field type
                        value = None
                        if 'valueString' in field_data:
                            value = field_data['valueString']
                        elif 'valueNumber' in field_data:
                            value = field_data['valueNumber']
                        elif 'valueDate' in field_data:
                            value = field_data['valueDate']
                        elif 'valueSelectionMark' in field_data:
                            value = field_data['valueSelectionMark']
                        elif 'content' in field_data:
                            value = field_data['content']

                        confidence = field_data.get('confidence', 0.0)

                        result_data["fields"][field_name] = {
                            "value": value,
                            "confidence": confidence,
                        }

                result_data["success"] = True
                break

            elif status == "failed":
                result_data["error"] = f"Analysis failed: {poll_data.get('error', 'Unknown error')}"
                break

        if attempt >= max_attempts:
            result_data["error"] = "Polling timed out after 2 minutes"

    except Exception as e:
        result_data["error"] = str(e)

    return result_data

# %% [markdown]
# ## 6. Process All Documents

# %%
# Process all documents
print(f"\nProcessing {len(input_files)} documents...")
print("=" * 60)

all_results = []
start_time = time.time()

for i, doc_path in enumerate(input_files):
    print(f"\n[{i+1}/{len(input_files)}] Analyzing: {doc_path.name}")

    result = analyze_document(MODEL_ID, doc_path)
    all_results.append(result)

    if result["success"]:
        print(f"  ✓ Success - {len(result['fields'])} fields extracted")
    else:
        print(f"  ✗ Failed - {result['error']}")

    # Rate limiting
    if i < len(input_files) - 1:
        time.sleep(DELAY_BETWEEN_REQUESTS)

elapsed = time.time() - start_time
print(f"\n\nBatch processing complete in {elapsed:.1f} seconds")

# %% [markdown]
# ## 7. Process Results

# %%
# Count successes and failures
successful = sum(1 for r in all_results if r["success"])
failed = len(all_results) - successful

print(f"\nResults Summary:")
print(f"  Successful: {successful}")
print(f"  Failed: {failed}")

if failed > 0:
    print("\nFailed documents:")
    for r in all_results:
        if not r["success"]:
            print(f"  - {r['document']}: {r['error']}")

# %% [markdown]
# ## 8. Create Results DataFrame

# %%
# Collect all unique field names
all_fields = set()
for result in all_results:
    if result["success"]:
        all_fields.update(result["fields"].keys())

all_fields = sorted(all_fields)
print(f"Total unique fields: {len(all_fields)}")

# %%
# Build DataFrame
rows = []

for result in all_results:
    row = {"document": result["document"], "success": result["success"]}

    if result["success"]:
        for field_name in all_fields:
            field_data = result["fields"].get(field_name, {})
            row[f"{field_name}"] = field_data.get("value")
            row[f"{field_name}_conf"] = field_data.get("confidence", 0.0)
    else:
        for field_name in all_fields:
            row[f"{field_name}"] = None
            row[f"{field_name}_conf"] = 0.0

    rows.append(row)

df = pd.DataFrame(rows)
print(f"\nDataFrame shape: {df.shape}")

# %%
# Display sample results
print("\nSample extraction results:")
print("-" * 60)

# Select a few key fields to display
display_fields = ["document", "success"]
key_fields = ["name", "date", "phone", "income1"]

for field in key_fields:
    if field in all_fields:
        display_fields.append(field)

if len(display_fields) > 2:
    print(df[display_fields].head(10).to_string())
else:
    print(df.head(10).to_string())

# %% [markdown]
# ## 9. Statistics

# %%
# Calculate confidence statistics per field
print("\nField Confidence Statistics:")
print("=" * 60)
print(f"{'Field Name':<35} {'Avg Conf':<12} {'Min':<10} {'Max'}")
print("-" * 60)

conf_cols = [c for c in df.columns if c.endswith("_conf")]

stats = []
for col in sorted(conf_cols):
    field_name = col.replace("_conf", "")
    avg_conf = df[col].mean()
    min_conf = df[col].min()
    max_conf = df[col].max()

    stats.append({
        "field": field_name,
        "avg": avg_conf,
        "min": min_conf,
        "max": max_conf,
    })

    print(f"{field_name:<35} {avg_conf:.2%}       {min_conf:.2%}     {max_conf:.2%}")

# %% [markdown]
# ## 10. Export Results

# %%
# Save results to CSV
csv_path = OUTPUTS_DIR / "batch_extraction_results.csv"
df.to_csv(csv_path, index=False)
print(f"Results saved to: {csv_path}")

# %%
# Save detailed JSON results
json_results = {
    "model_id": MODEL_ID,
    "total_documents": len(all_results),
    "successful": successful,
    "failed": failed,
    "results": all_results,
}

json_path = OUTPUTS_DIR / "batch_extraction_detailed.json"
save_json(json_results, json_path)
print(f"Detailed results saved to: {json_path}")

# %% [markdown]
# ## 11. Summary Report

# %%
print("\n" + "=" * 70)
print("BATCH ANALYSIS REPORT")
print("=" * 70)

print(f"\nModel: {MODEL_ID}")
print(f"Documents processed: {len(all_results)}")
print(f"Success rate: {successful/len(all_results):.1%}")

# Overall confidence
all_confidences = []
for result in all_results:
    if result["success"]:
        for field_data in result["fields"].values():
            if "confidence" in field_data:
                all_confidences.append(field_data["confidence"])

if all_confidences:
    avg_overall = sum(all_confidences) / len(all_confidences)
    print(f"Average confidence: {avg_overall:.1%}")

    high_conf = sum(1 for c in all_confidences if c >= 0.8)
    med_conf = sum(1 for c in all_confidences if 0.5 <= c < 0.8)
    low_conf = sum(1 for c in all_confidences if c < 0.5)

    print(f"\nConfidence distribution:")
    print(f"  High (>= 80%): {high_conf} ({high_conf/len(all_confidences):.1%})")
    print(f"  Medium (50-80%): {med_conf} ({med_conf/len(all_confidences):.1%})")
    print(f"  Low (< 50%): {low_conf} ({low_conf/len(all_confidences):.1%})")

# Low confidence fields
print("\nLowest confidence fields (may need review):")
low_conf_stats = [s for s in stats if s["avg"] < 0.5]
for s in sorted(low_conf_stats, key=lambda x: x["avg"])[:5]:
    print(f"  - {s['field']}: {s['avg']:.1%}")

print("\nOutput files:")
print(f"  - {csv_path}")
print(f"  - {json_path}")

# %%
print("\n" + "=" * 70)
print("WORKFLOW COMPLETE")
print("=" * 70)
print("\nYou have successfully:")
print("  1. Prepared and aligned training images")
print("  2. Generated OCR output for all images")
print("  3. Created label files for training")
print("  4. Uploaded training data to Azure Blob Storage")
print("  5. Trained a custom template model")
print("  6. Analyzed documents with the trained model")
print("  7. Processed documents in batch mode")
print("\nNext steps:")
print("  - Review low-confidence extractions")
print("  - Add more training samples if accuracy is insufficient")
print("  - Integrate the model into your application")

# %%
