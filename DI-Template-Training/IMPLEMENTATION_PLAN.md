# DI-Template-Training Implementation Plan

## Overview

This plan outlines the implementation of a notebook-based workflow for training and using Azure Document Intelligence template models via API. The workflow leverages existing alignment code from `/Template-alignment` to prepare images and generate the required label files.

## Architecture

```
DI-Template-Training/
├── notebooks/                          # Percent-format Python notebook files
│   ├── 01_setup_and_configuration.py   # Environment setup, Azure connection test
│   ├── 02_prepare_training_data.py     # Align images, copy to data folder
│   ├── 03_generate_ocr_json.py         # Run Layout API, generate .ocr.json files
│   ├── 04_generate_labels.py           # Generate fields.json and .labels.json
│   ├── 05_upload_to_blob.py            # Upload training data to Azure Blob Storage
│   ├── 06_train_model.py               # Build/train the custom template model
│   ├── 07_analyze_documents.py         # Use trained model for extraction
│   └── 08_batch_analysis.py            # Batch processing with trained model
├── src/                                # Reusable library modules
│   ├── __init__.py
│   ├── azure_client.py                 # Azure DI client wrapper
│   ├── blob_storage.py                 # Azure Blob Storage utilities
│   ├── ocr_generator.py                # .ocr.json generation from Layout API
│   ├── labels_generator.py             # fields.json and .labels.json generation
│   ├── alignment_wrapper.py            # Wrapper for Template-alignment code
│   └── utils.py                        # Common utilities
├── data/
│   ├── inputs/                         # Raw input images (copied from Template-alignment)
│   │   └── sample_forms/               # Training images
│   ├── aligned/                        # Aligned images ready for upload
│   ├── training/                       # Training dataset (to be uploaded to Azure)
│   │   ├── fields.json                 # Field schema definition
│   │   ├── image1.jpg                  # Aligned training image 1
│   │   ├── image1.jpg.ocr.json         # OCR output for image 1
│   │   ├── image1.jpg.labels.json      # Labels for image 1
│   │   └── ...                         # Additional training samples
│   └── outputs/                        # Analysis results
├── templates/                          # Template files from Template-alignment
│   ├── template.json                   # COCO format template definition
│   └── template.jpg                    # Template reference image
├── pyproject.toml                      # Poetry dependencies
├── sample.env                          # Environment variable template
├── .env                                # Actual environment variables (gitignored)
├── .python-version                     # Python version (3.11)
└── README.md                           # Project documentation
```

---

## Notebook Breakdown

### Notebook 1: Setup and Configuration (`01_setup_and_configuration.py`)

**Purpose:** Initialize environment, verify Azure credentials, test connectivity

**Cells:**
1. **[markdown]** Introduction and prerequisites
2. **[code]** Load environment variables from .env
3. **[code]** Initialize Azure Document Intelligence client
4. **[code]** Test connection by listing existing models
5. **[code]** Initialize Azure Blob Storage client
6. **[code]** Test blob storage connection (list containers)
7. **[markdown]** Configuration summary and next steps

**Key Dependencies:**
- `azure-ai-documentintelligence`
- `azure-storage-blob`
- `python-dotenv`

**Environment Variables Required:**
```
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://<resource>.cognitiveservices.azure.com
AZURE_DOCUMENT_INTELLIGENCE_KEY=<key>
AZURE_STORAGE_CONNECTION_STRING=<connection_string>
AZURE_STORAGE_CONTAINER_NAME=di-training-data
```

---

### Notebook 2: Prepare Training Data (`02_prepare_training_data.py`)

**Purpose:** Copy images from Template-alignment, align them to template, prepare for OCR

**Cells:**
1. **[markdown]** Overview of data preparation workflow
2. **[code]** Setup paths and import alignment modules from Template-alignment
3. **[code]** List available sample forms from Template-alignment
4. **[code]** Copy sample forms to local data/inputs folder
5. **[code]** Load template image and configuration
6. **[code]** Align each input image to template (using existing alignment code)
7. **[code]** Save aligned images to data/aligned folder
8. **[code]** Generate alignment quality report (inlier ratio, reprojection error)
9. **[code]** Visual comparison: original vs aligned (sample)
10. **[markdown]** Summary and next steps

**Reuses from Template-alignment:**
- `src/alignment/phase_1_alignment.py` - `FeatureBasedAligner`, `AlignmentConfig`
- `src/visualization/diff_visualization.py` - `create_red_overlay_diff`

**Output:**
- Aligned images in `data/aligned/`
- Alignment quality metrics report

---

### Notebook 3: Generate OCR JSON (`03_generate_ocr_json.py`)

**Purpose:** Run Azure Layout API on aligned images to generate .ocr.json files

**Cells:**
1. **[markdown]** Overview of OCR JSON generation
2. **[code]** Import dependencies and initialize Azure DI client
3. **[code]** List aligned images ready for processing
4. **[code]** Define function to capture raw Layout API response
5. **[code]** Process single image (with detailed output)
6. **[code]** Batch process all aligned images
7. **[code]** Save .ocr.json files alongside images in data/training folder
8. **[code]** Verify OCR JSON structure (sample inspection)
9. **[markdown]** Summary: files generated, page dimensions, word counts

**Key Azure API:**
```python
client.begin_analyze_document(
    "prebuilt-layout",
    body=image_bytes,
    content_type="application/octet-stream",
    cls=callback_to_capture_raw_response
)
```

**Output:**
- `data/training/*.jpg.ocr.json` files for each aligned image

---

### Notebook 4: Generate Labels (`04_generate_labels.py`)

**Purpose:** Generate fields.json and .labels.json files from template zones and OCR output

**Cells:**
1. **[markdown]** Overview of label generation process
2. **[code]** Import template loading utilities from Template-alignment
3. **[code]** Load template.json (COCO format with zones)
4. **[code]** Parse categories into field definitions
5. **[code]** Generate fields.json (field schema for Azure DI)
6. **[code]** Define bounding box normalization functions
7. **[code]** For each image: load .ocr.json, extract words/bboxes
8. **[code]** Map OCR words to template zones (using polygon/bbox intersection)
9. **[code]** Generate .labels.json for each image
10. **[code]** Validate labels format against Azure DI schema
11. **[code]** Visual inspection: show labeled regions on sample image
12. **[markdown]** Summary and validation results

**Key Logic:**
- Convert pixel coordinates to normalized 0-1 scale
- Match OCR words to template zones using spatial intersection
- Handle checkbox fields (selectionMark type)
- Handle text fields (string type)
- Handle numeric fields (number type)

**Output:**
- `data/training/fields.json` - field schema
- `data/training/*.jpg.labels.json` - labels for each training image

**Fields.json Structure:**
```json
{
  "fields": [
    {"name": "name", "type": "string"},
    {"name": "date", "type": "date", "subtype": "dmy"},
    {"name": "phone", "type": "string"},
    {"name": "income1", "type": "number"},
    {"name": "checkbox_need_assistance_yes", "type": "selectionMark"},
    ...
  ]
}
```

**Labels.json Structure:**
```json
{
  "document": "image1.jpg",
  "labels": [
    {
      "label": "name",
      "value": [{
        "page": 1,
        "text": "John Doe",
        "boundingBoxes": [[x1_norm, y1_norm, x2_norm, y1_norm, x2_norm, y2_norm, x1_norm, y2_norm]]
      }],
      "labelType": "Words"
    }
  ]
}
```

---

### Notebook 5: Upload to Blob Storage (`05_upload_to_blob.py`)

**Purpose:** Upload training data (images, .ocr.json, .labels.json, fields.json) to Azure Blob Storage

**Cells:**
1. **[markdown]** Overview of upload process
2. **[code]** Initialize Azure Blob Storage client
3. **[code]** Create/verify training container exists
4. **[code]** List files to upload from data/training folder
5. **[code]** Validate all required files present (fields.json, min 5 samples with ocr+labels)
6. **[code]** Upload files to blob container (with progress)
7. **[code]** Generate SAS URL for training container
8. **[code]** Verify upload by listing blob contents
9. **[code]** Save SAS URL to config for training step
10. **[markdown]** Summary and SAS URL display

**Key Azure API:**
```python
blob_service_client = BlobServiceClient.from_connection_string(conn_str)
container_client = blob_service_client.get_container_client(container_name)
blob_client.upload_blob(data, overwrite=True)
```

**Output:**
- Training data uploaded to Azure Blob Storage
- SAS URL saved for model training

---

### Notebook 6: Train Model (`06_train_model.py`)

**Purpose:** Build/train custom template model using Azure DI API

**Cells:**
1. **[markdown]** Overview of model training
2. **[code]** Initialize Azure DI client
3. **[code]** Load SAS URL from previous step
4. **[code]** Configure model parameters (model_id, description, buildMode)
5. **[code]** Start model training (build_document_model)
6. **[code]** Poll for training completion (with progress updates)
7. **[code]** Display training results (status, accuracy, docTypes)
8. **[code]** List all custom models in resource
9. **[code]** Save model_id to config for analysis step
10. **[markdown]** Summary and model details

**Key Azure API:**
```python
poller = client.begin_build_document_model(
    BuildDocumentModelRequest(
        model_id="my-template-model",
        description="Custom template model",
        build_mode="template",
        azure_blob_source=AzureBlobSource(container_url=sas_url)
    )
)
model = poller.result()
```

**Output:**
- Trained custom model in Azure DI
- Model ID saved for analysis

---

### Notebook 7: Analyze Documents (`07_analyze_documents.py`)

**Purpose:** Use trained model to analyze new documents and extract fields

**Cells:**
1. **[markdown]** Overview of document analysis
2. **[code]** Initialize Azure DI client
3. **[code]** Load trained model_id
4. **[code]** Select test document (not from training set)
5. **[code]** Option A: Analyze from local file
6. **[code]** Option B: Analyze from URL
7. **[code]** Parse analysis results (fields, confidence scores)
8. **[code]** Display extracted data in structured format
9. **[code]** Visualize extraction on document image
10. **[code]** Export results to JSON
11. **[markdown]** Summary and interpretation

**Key Azure API:**
```python
poller = client.begin_analyze_document(
    model_id="my-template-model",
    body=document_bytes,
    content_type="application/octet-stream"
)
result = poller.result()
```

**Output:**
- Extracted field values with confidence scores
- Visualization of extraction regions
- JSON export of results

---

### Notebook 8: Batch Analysis (`08_batch_analysis.py`)

**Purpose:** Process multiple documents using trained model

**Cells:**
1. **[markdown]** Overview of batch processing
2. **[code]** Initialize Azure DI client
3. **[code]** Load trained model_id
4. **[code]** List documents to process
5. **[code]** Define batch processing function (with rate limiting)
6. **[code]** Process all documents
7. **[code]** Aggregate results into DataFrame
8. **[code]** Export batch results to CSV/JSON
9. **[code]** Generate accuracy report (if ground truth available)
10. **[markdown]** Summary and statistics

**Output:**
- Batch extraction results (CSV/JSON)
- Processing statistics
- Optional accuracy report

---

## Source Modules (`src/`)

### `azure_client.py`
```python
# Azure Document Intelligence client wrapper
# - Connection management
# - Retry logic
# - Error handling
```

### `blob_storage.py`
```python
# Azure Blob Storage utilities
# - Upload/download files
# - SAS URL generation
# - Container management
```

### `ocr_generator.py`
```python
# .ocr.json generation
# - Layout API wrapper
# - Raw response capture
# - OCR JSON formatting
```

### `labels_generator.py`
```python
# Label generation utilities
# - fields.json creation from template
# - .labels.json creation from OCR + template zones
# - Bounding box normalization
# - Zone-to-word matching
```

### `alignment_wrapper.py`
```python
# Wrapper for Template-alignment code
# - Path management
# - Import helpers
# - Alignment convenience functions
```

### `utils.py`
```python
# Common utilities
# - File I/O
# - Image loading
# - JSON utilities
# - Progress display
```

---

## Environment Setup

### `sample.env`
```env
# Azure Document Intelligence
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://<resource-name>.cognitiveservices.azure.com
AZURE_DOCUMENT_INTELLIGENCE_KEY=<your-api-key>

# Azure Blob Storage
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=<account>;AccountKey=<key>;EndpointSuffix=core.windows.net
AZURE_STORAGE_CONTAINER_NAME=di-training-data

# Model Configuration
DI_MODEL_ID=my-template-model
DI_MODEL_DESCRIPTION=Custom template model for form extraction

# Paths
TEMPLATE_ALIGNMENT_PATH=../Template-alignment
```

### `pyproject.toml`
```toml
[project]
name = "di-template-training"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "azure-ai-documentintelligence>=1.0.0",
    "azure-storage-blob>=12.0.0",
    "python-dotenv>=1.0.0",
    "opencv-python>=4.12.0",
    "numpy>=1.24.0",
    "matplotlib>=3.8.0",
    "pandas>=2.0.0",
    "shapely>=2.0.0",  # For polygon intersection
]

[dependency-groups]
dev = [
    "ipykernel>=7.1.0",
]

[build-system]
requires = ["poetry-core>=2.0.0"]
build-backend = "poetry.core.masonry.api"
```

---

## Key Implementation Details

### 1. Alignment Integration
The alignment process from Template-alignment will be reused:
```python
# Import from Template-alignment
sys.path.insert(0, str(TEMPLATE_ALIGNMENT_PATH / 'src'))
from alignment.phase_1_alignment import FeatureBasedAligner, AlignmentConfig
```

### 2. Labels Generation Strategy
The critical step is mapping OCR words to template zones:

1. Load template zones (polygons/rectangles) from template.json
2. Load OCR results from .ocr.json
3. For each template zone:
   - Find OCR words that intersect with the zone
   - Concatenate text from matching words
   - Extract normalized bounding boxes
   - Create label entry

### 3. Bounding Box Normalization
Azure DI requires normalized coordinates (0-1 scale):
```python
def normalize_bbox(bbox, page_width, page_height):
    """Convert pixel bbox to normalized coordinates."""
    x, y, w, h = bbox
    return [
        x / page_width,           # x1
        y / page_height,          # y1
        (x + w) / page_width,     # x2
        y / page_height,          # y1
        (x + w) / page_width,     # x2
        (y + h) / page_height,    # y2
        x / page_width,           # x1
        (y + h) / page_height     # y2
    ]
```

### 4. Field Type Mapping
Map template categories to Azure DI field types:
```python
FIELD_TYPE_MAP = {
    # Checkbox fields -> selectionMark
    "checkbox_*": "selectionMark",
    # Date fields
    "date": {"type": "date", "subtype": "ymd"},
    "spouse_date": {"type": "date", "subtype": "ymd"},
    # Numeric fields
    "income*": "number",
    "spouse_income*": "number",
    # Text fields (default)
    "*": "string"
}
```

---

## Implementation Order

1. **Phase 1: Project Setup**
   - Create directory structure
   - Create pyproject.toml and sample.env
   - Create README.md

2. **Phase 2: Source Modules**
   - Implement src/utils.py
   - Implement src/alignment_wrapper.py
   - Implement src/azure_client.py
   - Implement src/blob_storage.py
   - Implement src/ocr_generator.py
   - Implement src/labels_generator.py

3. **Phase 3: Notebooks (in order)**
   - 01_setup_and_configuration.py
   - 02_prepare_training_data.py
   - 03_generate_ocr_json.py
   - 04_generate_labels.py
   - 05_upload_to_blob.py
   - 06_train_model.py
   - 07_analyze_documents.py
   - 08_batch_analysis.py

---

## Validation Checkpoints

### Before Training
- [ ] At least 5 aligned images in data/training/
- [ ] Each image has corresponding .ocr.json file
- [ ] Each image has corresponding .labels.json file
- [ ] fields.json contains all expected fields
- [ ] All bounding boxes are normalized (0-1 range)
- [ ] Labels reference valid OCR text

### After Training
- [ ] Model status is "succeeded"
- [ ] Model accuracy meets minimum threshold (>80%)
- [ ] Test extraction returns expected fields

---

## Error Handling

Common issues and solutions:

1. **Alignment failure**: Use "difficult" mode for poor quality scans
2. **OCR timeout**: Reduce image size before Layout API call
3. **Label mismatch**: Verify zone coordinates match OCR word positions
4. **Training failure**: Check blob container permissions, verify file structure
5. **Rate limiting**: Implement exponential backoff for API calls

---

## Notes

- All notebooks use percent format (`# %%`) for VS Code compatibility
- Environment variables are loaded from .env via python-dotenv
- Poetry is used for dependency management (consistent with Template-alignment)
- Aligned images are JPEG format for optimal Azure DI compatibility
- Minimum 5 training samples required, recommended 10-15 for best accuracy
