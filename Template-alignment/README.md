
# Template Alignment Project Setup Guide

## The Problem
Installing PaddleOCR 3.3.2 with Poetry fails on Python 3.12+ due to a broken dependency (`bce-python-sdk`) that has build issues.

## The Solution
Use Python 3.11.14 managed by pyenv, create a Poetry environment, and work around VSCode/WSL Jupyter kernel bugs.

---

## Step 1: Install System Dependencies (WSL/Ubuntu)

```

sudo apt update
sudo apt install -y build-essential libssl-dev zlib1g-dev \
libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev \
libffi-dev liblzma-dev

```

---

## Step 2: Install pyenv (Python Version Manager)

```


# Install pyenv

curl https://pyenv.run | bash

# Add to ~/.bashrc (or ~/.zshrc)

export PYENV_ROOT="$HOME/.pyenv"
command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

# Reload shell

source ~/.bashrc

```

---

## Step 3: Install Python 3.11.14

```

pyenv install 3.11.14

```

---

## Step 4: Set Up Project

```

cd ~/GitHub/ai-adoption-research-and-development/Template-alignment

# Set Python version for this directory

pyenv local 3.11.14

# Verify

python --version  \# Should show Python 3.11.14

```

---

## Step 5: Initialize Poetry Project

```


# Initialize Poetry (creates pyproject.toml)

poetry init -n

# Tell Poetry to use Python 3.11.14

poetry env use python

# Verify Poetry is using correct Python

poetry env info

```

---

## Step 6: Install Dependencies

```


# Install PaddleOCR and dependencies

poetry add paddleocr
poetry add paddlepaddle  \# Core framework (required but not auto-installed)
poetry add opencv-python

# Install development tools (older ipykernel to avoid VSCode freezing)

poetry add ipykernel@~6.29 --group dev

```

---

## Step 7: Configure VSCode

### Option A: Auto-detect interpreter
1. Press `Ctrl+Shift+P`
2. Type: `Python: Select Interpreter`
3. Choose: `Python 3.11.14 ('template-alignment-...' : poetry)`

### Option B: Manual path (if not showing)
```


# Get the exact path

echo "\$(poetry env info --path)/bin/python"

```

1. Press `Ctrl+Shift+P`
2. Type: `Python: Select Interpreter`
3. Click `Enter interpreter path...`
4. Paste the path from above

### Reload VSCode
Press `Ctrl+Shift+P` → `Developer: Reload Window`

---

## Step 8: Fix WSL Performance Issues (Optional but Recommended)

Create `C:\Users\YourUsername\.wslconfig` on Windows:

```

[wsl2]
memory=8GB
processors=4

```

Restart WSL from PowerShell:
```

wsl --shutdown

```

---

## Step 9: Verify Everything Works

```


# Activate Poetry environment

poetry shell

# Test imports

python -c "import paddle; import paddleocr; import cv2; print('All imports successful!')"

# Check Python version

python --version  \# Should be 3.11.14

```

---

## Running Your Code

### Interactive cells (# %%)
- Open your `.py` file with `# %%` markers
- Click "Run Cell" or press `Shift+Enter`
- Kernel should show: `Python 3.11.14 ('template-alignment-...')`

### Regular Python scripts
```

poetry run python your_script.py

```

### Or activate the environment first
```

poetry shell
python your_script.py

```

---

## Troubleshooting

### Kernel keeps freezing
```

poetry remove ipykernel
poetry add ipykernel@~6.29 --group dev

```
Then reload VSCode.

### Wrong Python version showing
```

rm -rf .venv
poetry env use python
poetry install

```

### "No module named 'paddle'"
```

poetry add paddlepaddle

```

### Clear stale kernels
```

poetry run jupyter kernelspec list
poetry run jupyter kernelspec remove template-alignment

```

---

## Why All This Was Needed

1. **Python 3.12+**: `bce-python-sdk` (PaddleOCR dependency) has broken build on 3.12+
2. **Python 3.11.14**: Latest stable version that works with PaddleOCR ecosystem
3. **pyenv**: Manages multiple Python versions (like nvm for Node.js)
4. **System libraries**: Required for building Python from source
5. **paddlepaddle**: Not auto-installed by paddleocr despite being required
6. **ipykernel 6.x**: Version 7.0+ freezes in VSCode/WSL
7. **WSL memory**: Default limits cause kernel timeouts

---

## Template Management

This project uses template-based document processing with both polygonal and rectangular field annotations. The template system supports form field detection and data extraction from scanned documents.

### Template Files

- **`template_polygonal.json`**: Contains polygonal segmentation annotations for text fields (name, signature, date, phone, etc.)
- **`template_rectangular.csv`**: Contains rectangular bounding box annotations for checkboxes and income fields
- **`template.json`**: Merged template file combining both polygonal and rectangular annotations in COCO format

### Merging Templates

To combine the polygonal and rectangular template data into a single unified format:

```bash
# Run the merge script
python merge_templates.py

# This creates template.json with:
# - 75 categories (all field types)
# - 75 annotations (all field locations)
# - Polygonal fields retain segmentation data
# - Rectangular fields use bounding box data
```

### Template Structure

The merged `template.json` follows COCO format:

```json
{
  "info": {"description": "my-project-name"},
  "images": [{"id": 1, "width": 2610, "height": 3348, "file_name": "template.jpg"}],
  "annotations": [
    {
      "id": 0,
      "category_id": 28,
      "segmentation": [[x1,y1,x2,y2,...]],  // Polygonal fields
      "bbox": [x,y,width,height],
      "area": 88880.8
    },
    {
      "id": 11,
      "category_id": 1,
      "bbox": [x,y,width,height],            // Rectangular fields
      "area": 2116.0
    }
  ],
  "categories": [
    {"id": 1, "name": "checkbox_need_assistance_yes"},
    {"id": 28, "name": "name"},
    // ... all 75 field types
  ]
}
```

### Field Types

**Checkboxes (IDs 1-22, 70-75):**
- Employment changes, school, shelter, family assets, etc.
- Both "yes/no" pairs for main applicant and spouse

**Text Fields (IDs 23-33):**
- `explain_changes`: Multi-line explanation
- `signature`, `spouse_signature`: Signature areas
- `date`, `spouse_date`: Date fields
- `name`, `spouse_name`: Name fields
- `phone`, `spouse_phone`: Phone numbers
- `sin`, `spouse_sin`: Social insurance numbers

**Income Fields (IDs 34-69):**
- `income1-income18`: Main applicant income lines
- `spouse_income1-spouse_income18`: Spouse income lines

### Using Templates in Code

```python
import json

# Load merged template
with open('template.json', 'r') as f:
    template_data = json.load(f)

# Access field definitions
categories = {cat['id']: cat['name'] for cat in template_data['categories']}
annotations = template_data['annotations']

# Find specific field
name_field = next(ann for ann in annotations
                 if categories[ann['category_id']] == 'name')

# Get field location
if 'segmentation' in name_field:
    # Polygonal field - use segmentation coordinates
    segmentation = name_field['segmentation'][0]
elif 'bbox' in name_field:
    # Rectangular field - use bounding box
    x, y, w, h = name_field['bbox']
```

---

## Project Structure

```

Template-alignment/
├── .python-version          \# pyenv auto-switches to 3.11.14
├── pyproject.toml           \# Poetry dependencies
├── poetry.lock              \# Locked versions
├── .venv/                   \# Virtual environment (Python 3.11.14)
└── your_scripts.py          \# Your code

```

---

## Key Commands Reference

```


# Python version management

pyenv local 3.11.14          \# Set for current directory
python --version             \# Check active version

# Poetry environment

poetry env use python        \# Create venv with pyenv's Python
poetry env info              \# Show venv details
poetry shell                 \# Activate venv
poetry install               \# Install all dependencies
poetry add package           \# Add new dependency

# VSCode

Ctrl+Shift+P → "Python: Select Interpreter"
Ctrl+Shift+P → "Developer: Reload Window"

```

---

## Final Dependencies

**Runtime:**
- paddleocr >=3.3.2
- paddlepaddle (required manually)
- opencv-python >=4.12.0

**Development:**
- ipykernel ~6.29 (avoid 7.0+ for VSCode stability)

All running on **Python 3.11.14** managed by **pyenv**.
