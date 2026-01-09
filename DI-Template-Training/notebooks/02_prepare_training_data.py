# %% [markdown]
# # 02 - Prepare Training Data
#
# This notebook prepares training images by:
# 1. Copying sample forms from Template-alignment
# 2. Aligning each image to the template
# 3. Saving aligned images for OCR processing
#
# The alignment ensures consistent positioning for accurate label generation.

# %%
# Standard imports
import os
import sys
import shutil
from pathlib import Path

import cv2
import numpy as np
import matplotlib.pyplot as plt

# Add project root to path
project_root = Path.cwd().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from src.utils import load_image, save_image, ensure_dir, print_progress
from src.alignment_wrapper import (
    get_template_paths,
    align_image_to_template,
    AlignmentMode,
)

print(f"Project root: {project_root}")

# %% [markdown]
# ## 1. Configuration

# %%
# Paths
DATA_DIR = project_root / "data"
INPUTS_DIR = DATA_DIR / "inputs" / "sample_forms"
ALIGNED_DIR = DATA_DIR / "aligned"
TEMPLATES_DIR = project_root / "templates"

# Alignment mode (options: DEFAULT, HIGH_ACCURACY, DIFFICULT, STRICT_QC)
ALIGNMENT_MODE = AlignmentMode.HIGH_ACCURACY

# Ensure directories exist
ensure_dir(INPUTS_DIR)
ensure_dir(ALIGNED_DIR)
ensure_dir(TEMPLATES_DIR)

print(f"Input directory: {INPUTS_DIR}")
print(f"Aligned output: {ALIGNED_DIR}")
print(f"Alignment mode: {ALIGNMENT_MODE.value}")

# %% [markdown]
# ## 2. Copy Sample Forms from Template-alignment

# %%
# Get paths from Template-alignment
ta_paths = get_template_paths()

print("Template-alignment paths:")
for name, path in ta_paths.items():
    print(f"  {name}: {path}")

# %%
# Copy template files
template_json_src = ta_paths["template_json"]
template_image_src = ta_paths["template_image"]

template_json_dst = TEMPLATES_DIR / "template.json"
template_image_dst = TEMPLATES_DIR / "template.jpg"

if not template_json_dst.exists():
    shutil.copy(template_json_src, template_json_dst)
    print(f"Copied template.json to {template_json_dst}")
else:
    print(f"template.json already exists at {template_json_dst}")

if not template_image_dst.exists():
    shutil.copy(template_image_src, template_image_dst)
    print(f"Copied template.jpg to {template_image_dst}")
else:
    print(f"template.jpg already exists at {template_image_dst}")

# %%
# Copy sample forms
sample_forms_src = ta_paths["sample_forms"]
sample_files = list(sample_forms_src.glob("*.jpg"))

print(f"\nFound {len(sample_files)} sample forms in Template-alignment")

copied_count = 0
for src_file in sample_files:
    dst_file = INPUTS_DIR / src_file.name
    if not dst_file.exists():
        shutil.copy(src_file, dst_file)
        copied_count += 1

print(f"Copied {copied_count} new files to {INPUTS_DIR}")

# List input files
input_files = sorted(INPUTS_DIR.glob("*.jpg"))
print(f"\nTotal input files ready: {len(input_files)}")
for f in input_files:
    print(f"  - {f.name}")

# %% [markdown]
# ## 3. Load Template Image

# %%
# Load template
template_image = load_image(template_image_dst)
print(f"Template image loaded: {template_image.shape}")

# Display template
plt.figure(figsize=(10, 12))
plt.imshow(cv2.cvtColor(template_image, cv2.COLOR_BGR2RGB))
plt.title("Template Image")
plt.axis("off")
plt.tight_layout()
plt.show()

# %% [markdown]
# ## 4. Align Images to Template

# %%
# Process all input images
alignment_results = []

print(f"\nAligning {len(input_files)} images using {ALIGNMENT_MODE.value} mode...")
print("-" * 60)

for i, input_path in enumerate(input_files):
    print(f"\n[{i+1}/{len(input_files)}] Processing: {input_path.name}")

    # Load input image
    input_image = load_image(input_path)

    # Align to template (verbose on first image, raise on first failure)
    result = align_image_to_template(
        input_image,
        template_image,
        mode=ALIGNMENT_MODE,
        verbose=(i == 0),  # Verbose for first image only
        raise_on_failure=(i == 0),  # Raise error on first failure to debug
    )

    # Save aligned image
    output_path = ALIGNED_DIR / input_path.name
    save_image(result.aligned_image, output_path)

    alignment_results.append({
        "filename": input_path.name,
        "success": result.success,
        "reprojection_error": result.reprojection_error,
        "inlier_ratio": result.inlier_ratio,
        "num_matches": result.num_matches,
        "message": result.message,
    })

    # Show status
    status = "OK" if result.success else "FAILED"
    print(f"  Status: {status} | Matches: {result.num_matches} | Inliers: {result.inlier_ratio:.1%}")

print("\n")

# %% [markdown]
# ## 5. Alignment Quality Report

# %%
print("Alignment Quality Report")
print("=" * 70)
print(f"{'Filename':<45} {'Error (px)':<12} {'Inliers %':<12} {'Status'}")
print("-" * 70)

successful = 0
for r in alignment_results:
    status = "OK" if r["success"] else "FAILED"
    if r["success"]:
        successful += 1

    error_str = f"{r['reprojection_error']:.2f}" if r['reprojection_error'] < float('inf') else "N/A"
    inlier_str = f"{r['inlier_ratio']:.1f}%"

    print(f"{r['filename']:<45} {error_str:<12} {inlier_str:<12} {status}")

print("-" * 70)
print(f"Total: {successful}/{len(alignment_results)} images aligned successfully")

# Quality thresholds
good_quality = sum(1 for r in alignment_results
                   if r["success"] and r["reprojection_error"] < 5.0 and r["inlier_ratio"] > 40)
print(f"High quality (error <5px, inliers >40%): {good_quality}/{len(alignment_results)}")

# %% [markdown]
# ## 6. Visual Comparison (Sample)

# %%
# Show before/after for first image
if input_files and alignment_results:
    sample_input = load_image(input_files[0])
    sample_aligned = load_image(ALIGNED_DIR / input_files[0].name)

    fig, axes = plt.subplots(1, 3, figsize=(18, 8))

    axes[0].imshow(cv2.cvtColor(sample_input, cv2.COLOR_BGR2RGB))
    axes[0].set_title(f"Original: {input_files[0].name}")
    axes[0].axis("off")

    axes[1].imshow(cv2.cvtColor(sample_aligned, cv2.COLOR_BGR2RGB))
    axes[1].set_title("Aligned")
    axes[1].axis("off")

    axes[2].imshow(cv2.cvtColor(template_image, cv2.COLOR_BGR2RGB))
    axes[2].set_title("Template")
    axes[2].axis("off")

    plt.tight_layout()
    plt.show()

# %% [markdown]
# ## 7. Summary

# %%
print("\n" + "=" * 60)
print("PREPARATION SUMMARY")
print("=" * 60)

aligned_files = list(ALIGNED_DIR.glob("*.jpg"))
print(f"\nAligned images saved: {len(aligned_files)}")
print(f"Location: {ALIGNED_DIR}")

if len(aligned_files) >= 5:
    print(f"\nMinimum requirement (5 images): MET")
    print("\nYou can proceed to the next notebook: 03_generate_ocr_json.py")
else:
    print(f"\nWARNING: Only {len(aligned_files)} images aligned.")
    print("Azure DI requires minimum 5 training samples.")
    print("Please add more sample forms to the input directory.")

# %%
