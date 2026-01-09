# DI-Template-Training

Azure Document Intelligence template model training via API, without using Document Intelligence Studio.

## Overview

This project provides a notebook-based workflow for:
1. Preparing training data (aligning images to a template)
2. Generating OCR output via Azure Layout API
3. Creating label files (fields.json, .labels.json)
4. Uploading training data to Azure Blob Storage
5. Training a custom template model
6. Analyzing documents with the trained model

## Prerequisites

- Python 3.11+
- Poetry for dependency management
- Azure Document Intelligence resource
- Azure Blob Storage account
- Training images (minimum 5, recommended 10-15)

## Setup

1. Clone and navigate to the project:
   ```bash
   cd DI-Template-Training
   ```

2. Install dependencies with Poetry:
   ```bash
   poetry install
   ```

3. Copy sample.env to .env and fill in your Azure credentials:
   ```bash
   cp sample.env .env
   # Edit .env with your values
   ```

4. Activate the virtual environment:
   ```bash
   poetry shell
   ```

## Notebooks

Run the notebooks in order using VS Code (with Jupyter extension) or any editor that supports percent-format notebooks:

| Notebook | Purpose |
|----------|---------|
| `01_setup_and_configuration.py` | Test Azure connectivity |
| `02_prepare_training_data.py` | Align images to template |
| `03_generate_ocr_json.py` | Generate .ocr.json files via Layout API |
| `04_generate_labels.py` | Create fields.json and .labels.json |
| `05_upload_to_blob.py` | Upload training data to Azure |
| `06_train_model.py` | Train custom template model |
| `07_analyze_documents.py` | Analyze single documents |
| `08_batch_analysis.py` | Batch process multiple documents |

## Project Structure

```
DI-Template-Training/
├── notebooks/           # Percent-format Python notebooks
├── src/                 # Reusable library modules
├── data/
│   ├── inputs/          # Raw input images
│   ├── aligned/         # Aligned images
│   ├── training/        # Training dataset for Azure
│   └── outputs/         # Analysis results
├── templates/           # Template files
├── pyproject.toml       # Dependencies
└── sample.env           # Environment template
```

## Integration with Template-alignment

This project reuses alignment code from the `/Template-alignment` project. Ensure that project is available at the path specified in `TEMPLATE_ALIGNMENT_PATH`.

## Azure Requirements

### Document Intelligence
- API version: 2024-11-30 or later
- Tier: S0 (Standard) for custom model training

### Blob Storage
- Container with read/write access
- SAS token generation capability

## Training Data Requirements

- Minimum 5 labeled documents (recommended 10-15)
- Consistent visual layout across documents
- Supported formats: JPEG, PNG, PDF
- Maximum 50 MB total training data
- Maximum 500 pages total
