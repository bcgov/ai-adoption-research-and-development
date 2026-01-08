# Code Reorganization Summary

This document describes the reorganization of the Template-alignment project to be notebook-driven with a clear library structure.

## New Structure

```
Template-alignment/
├── src/                          # Library code (reusable modules)
│   ├── __init__.py
│   ├── alignment/               # Image alignment module
│   │   ├── __init__.py
│   │   └── phase_1_alignment.py
│   ├── ocr/                     # OCR extraction module
│   │   ├── __init__.py
│   │   ├── ocr_extraction.py
│   │   └── debug_utils.py
│   ├── detection/               # Detection module
│   │   ├── __init__.py
│   │   └── checkbox_detection.py
│   ├── visualization/           # Visualization module
│   │   ├── __init__.py
│   │   └── diff_visualization.py
│   └── template/                # Template processing module (NEW)
│       ├── __init__.py
│       ├── config.py            # Configuration constants
│       ├── template_loader.py   # Template loading utilities
│       └── template_processing.py  # Template processing utilities
│
├── notebooks/                    # Jupyter notebook workflows (main entry point)
│   ├── 01_alignment_experiments.ipynb      # Alignment configuration experiments
│   ├── 02_single_document_processing.ipynb  # Single document OCR pipeline
│   ├── 03_batch_processing.ipynb           # Batch document processing
│   └── 04_accuracy_evaluation.ipynb        # OCR accuracy evaluation
│
├── scripts/                     # Utility scripts (non-notebook)
│   └── merge_templates.py       # Template merging utility
│
├── data/                        # All data files
│   ├── templates/              # Template definitions
│   │   ├── template.jpg
│   │   ├── template.json
│   │   ├── template_polygonal.json
│   │   └── template_rectangular.csv
│   ├── inputs/                  # Input documents
│   │   ├── sample_forms/        # Batch input images
│   │   └── input_document.jpg   # Single test document
│   └── ground_truth/            # Ground truth data
│       └── sample_form_true_data/  # Ground truth JSON files
│
├── outputs/                     # All generated outputs
│   ├── processed/              # Processed documents
│   │   ├── json_data/          # Extracted JSON data
│   │   └── extracted_data.json # Single document output
│   ├── visualizations/         # Debug images
│   │   └── debug_data/         # Per-document debug artifacts
│   └── reports/                # Reports
│       ├── ocr_accuracy_report.txt
│       └── debug_slices/       # OCR slice debugging
│
├── pyproject.toml              # Poetry config
├── poetry.lock                 # Poetry lock
├── .python-version             # pyenv version
└── README.md                   # Documentation
```

## Key Changes

### 1. Library Code Extraction
- **New module**: `src/template/` - Contains template loading and processing utilities extracted from `template_ocr_pipeline.py`
  - `template_loader.py`: Functions to load and parse template JSON files
  - `template_processing.py`: Mask creation, ROI extraction, checkbox detection
  - `config.py`: Configuration constants (ROI_PADDING, OCR settings, etc.)

### 2. Notebook-Driven Workflow
- All executable workflows are now in Jupyter notebooks:
  - `01_alignment_experiments.ipynb`: Test different alignment configurations
  - `02_single_document_processing.ipynb`: Process a single document end-to-end
  - `03_batch_processing.ipynb`: Process multiple documents in batch
  - `04_accuracy_evaluation.ipynb`: Evaluate OCR accuracy against ground truth

### 3. Organized Data Structure
- **Templates**: All template files in `data/templates/`
- **Inputs**: Input documents in `data/inputs/`
- **Ground Truth**: Reference data in `data/ground_truth/`
- **Outputs**: All generated files in `outputs/` with clear subdirectories

### 4. Updated Imports

**Old imports:**
```python
from phase_1_alignment import FeatureBasedAligner
from ocr_extraction import FastOCRExtractor
from template_ocr_pipeline import load_zones_from_template
```

**New imports:**
```python
from src.alignment.phase_1_alignment import FeatureBasedAligner
from src.ocr.ocr_extraction import FastOCRExtractor
from src.template import load_zones_from_template
```

## Migration Notes

### Functions Extracted to Library
The following functions were extracted from `template_ocr_pipeline.py` to `src/template/`:
- `load_template()` → `src/template/template_loader.py`
- `load_zones_from_template()` → `src/template/template_loader.py`
- `build_union_mask()` → `src/template/template_processing.py`
- `apply_mask()` → `src/template/template_processing.py`
- `extract_polygon_roi()` → `src/template/template_processing.py`
- `detect_checkboxes_from_template_image()` → `src/template/template_processing.py`
- Configuration constants → `src/template/config.py`

### File Path Updates
All file paths in notebooks have been updated to use the new structure:
- Template files: `data/templates/`
- Input images: `data/inputs/`
- Output JSON: `outputs/processed/`
- Debug images: `outputs/visualizations/` and `outputs/reports/debug_slices/`

## Usage

### Running Notebooks
1. Open any notebook in `notebooks/`
2. Ensure the Python kernel is set to the Poetry environment (Python 3.11.14)
3. Run cells sequentially

### Using Library Code
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src.template import load_zones_from_template, ROI_PADDING
from src.alignment import FeatureBasedAligner, AlignmentConfig
from src.ocr import FastOCRExtractor
```

### Running Utility Scripts
```bash
poetry run python scripts/merge_templates.py
```

## Benefits

1. **Clear Separation**: Library code vs notebooks vs data vs outputs
2. **Notebook-Driven**: All workflows are in notebooks for interactive exploration
3. **Reusable Modules**: Library code can be imported and reused
4. **Organized Data**: Clear structure for inputs, templates, and outputs
5. **Scalable**: Easy to add new notebooks or modules
6. **Standard Layout**: Follows common Python project structure

## Old Files (Can Be Removed)

The following old files can be removed after verifying notebooks work:
- `notebook.py` (replaced by `notebooks/01_alignment_experiments.ipynb`)
- `template_ocr_pipeline.py` (functions extracted to `src/template/`, workflow in `notebooks/02_single_document_processing.ipynb`)
- `batch_template_ocr.py` (replaced by `notebooks/03_batch_processing.ipynb`)
- `ocr_accuracy_report.py` (replaced by `notebooks/04_accuracy_evaluation.ipynb`)
- `merge_templates.py` (moved to `scripts/merge_templates.py`)

Note: Keep old files until you've verified the notebooks work correctly!
