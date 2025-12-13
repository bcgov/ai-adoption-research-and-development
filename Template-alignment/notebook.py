# %% [markdown]
# ## Pre-Alignment Baseline: Original Differences
# This shows the differences between template and input BEFORE any alignment processing.
# Use this to understand how misaligned the input document is initially.

# %%
import cv2
from diff_visualization import create_red_overlay_diff

# Load images for baseline comparison
template = cv2.imread('template.jpg')
input_img = cv2.imread('input_document.jpg')

# Generate baseline red overlay diff - shows original misalignment
baseline_red_overlay = create_red_overlay_diff(
    template,
    input_img,
    threshold=30,
    alpha=0.6
)
cv2.imwrite('baseline_before_alignment_red_overlay.jpg', baseline_red_overlay)

# %%
# ## Default (fast ORB)
# Uses ORB with balanced settings: reasonably strict matching, standard RANSAC threshold, and a minimum of 10 matches.
# Good general-purpose choice for clean scans where you want speed and reliability without tuning.

# %%
import cv2
import json
from phase_1_alignment import FeatureBasedAligner, AlignmentConfig
from diff_visualization import create_red_overlay_diff
from ocr_extraction import FastOCRExtractor, load_extraction_zones, visualize_extractions


# Load your images
template = cv2.imread('template.jpg')
input_img = cv2.imread('input_document.jpg')


# Configure and align
config = AlignmentConfig(
    feature_detector="ORB",
    max_features=5000,
    ratio_test_threshold=0.7,
    ransac_threshold=5.0,
    min_matches=10,
    verbose=True
)

aligner = FeatureBasedAligner(config)
result = aligner.align(input_img, template)

# Save outputs
cv2.imwrite('aligned_default_orb.jpg', result.aligned_image)

red_overlay = create_red_overlay_diff(template, result.aligned_image, threshold=30, alpha=0.6)
cv2.imwrite('aligned_default_orb_red_overlay.jpg', red_overlay)

print(f"[DEFAULT] Error: {result.reprojection_error:.2f}px, Inliers: {result.inlier_ratio:.1f}%")


# ============================================================================
# FAST OCR EXTRACTION (PaddleOCR - CORRECT API)
# ============================================================================

# Load extraction zones
zones = load_extraction_zones('labels_my-project-name_2025-12-11-01-43-24.csv')
print(f"\n[OCR] Found {len(zones)} fields to extract")

# Initialize FAST OCR extractor (CORRECT - only lang parameter)
extractor = FastOCRExtractor(lang='en', verbose=True)

# Extract text (FAST - typically 0.5-2 seconds total)
extracted_data = extractor.extract_fields(
    result.aligned_image,
    zones,
    preprocess=True
)

# Save JSON
output = {name: data['text'] for name, data in extracted_data.items()}
with open('extracted_data.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

# Visualize
visualize_extractions(result.aligned_image, extracted_data, 'extraction_visualization.jpg')

# Print results
print("\n[OCR] Extracted data:")
for name, data in extracted_data.items():
    conf_icon = "✓" if data['confidence'] > 0.5 else "⚠"
    print(f"  {conf_icon} {name:25s}: '{data['text']}' (conf: {data['confidence']:.2f})")

print(f"\n[OCR] Saved JSON to: extracted_data.json")




# %%
# ## High Accuracy (SIFT)
# Switches to SIFT with otherwise standard thresholds.
# Better when documents may be rotated, slightly distorted, or you want the most accurate homography and can afford extra runtime.

# %%
import cv2
from phase_1_alignment import FeatureBasedAligner, AlignmentConfig
from diff_visualization import create_red_overlay_diff

template = cv2.imread('template.jpg')
input_img = cv2.imread('input_document.jpg')

# High-accuracy SIFT configuration
config = AlignmentConfig(
    feature_detector="SIFT",      # More accurate, slower
    max_features=5000,
    ratio_test_threshold=0.7,     # Standard Lowe ratio
    ransac_threshold=5.0,         # Standard RANSAC threshold
    min_matches=10,
    verbose=True
)

aligner = FeatureBasedAligner(config)
result = aligner.align(input_img, template)

cv2.imwrite('aligned_accurate_sift.jpg', result.aligned_image)

# Create red overlay diff
red_overlay = create_red_overlay_diff(
    template,
    result.aligned_image,
    threshold=30,
    alpha=0.6
)
cv2.imwrite('aligned_accurate_sift_red_overlay.jpg', red_overlay)

print(f"[ACCURATE SIFT] Error: {result.reprojection_error:.2f}px, Inliers: {result.inlier_ratio:.1f}%")

# %%
# ## Difficult Documents (relaxed, SIFT)
# Still uses SIFT but relaxes the matching and RANSAC thresholds, and allows fewer matches while looking for more features.
# Intended for low-contrast, noisy, partially visible, or otherwise "hard" documents where default settings fail due to too few inliers.

# %%
import cv2
from phase_1_alignment import FeatureBasedAligner, AlignmentConfig
from diff_visualization import create_red_overlay_diff

template = cv2.imread('template.jpg')
input_img = cv2.imread('input_document.jpg')

# Relaxed config for low-contrast / noisy / partially visible docs
config = AlignmentConfig(
    feature_detector="SIFT",
    max_features=8000,            # Look for more features
    ratio_test_threshold=0.8,     # More lenient matching
    ransac_threshold=7.0,         # More tolerant RANSAC
    min_matches=8,                # Allow fewer matches
    verbose=True
)

aligner = FeatureBasedAligner(config)
result = aligner.align(input_img, template)

cv2.imwrite('aligned_difficult.jpg', result.aligned_image)

# Create red overlay diff
red_overlay = create_red_overlay_diff(
    template,
    result.aligned_image,
    threshold=30,
    alpha=0.6
)
cv2.imwrite('aligned_difficult_red_overlay.jpg', red_overlay)

print(f"[DIFFICULT] Error: {result.reprojection_error:.2f}px, Inliers: {result.inlier_ratio:.1f}%")
# %%
# ## Strict Quality Control
# Uses SIFT with stricter ratio test, tighter RANSAC threshold, and higher minimum matches.
# Designed for production quality gates where you only accept very precise alignments and are okay with rejecting marginal cases.

# %%
import cv2
from phase_1_alignment import FeatureBasedAligner, AlignmentConfig
from diff_visualization import create_red_overlay_diff

template = cv2.imread('template.jpg')
input_img = cv2.imread('input_document.jpg')

# Strict configuration for QC (reject marginal alignments)
config = AlignmentConfig(
    feature_detector="SIFT",
    max_features=6000,
    ratio_test_threshold=0.65,    # Stricter Lowe ratio
    ransac_threshold=3.0,         # Tight inlier threshold
    min_matches=20,               # Require more matches
    verbose=True
)

aligner = FeatureBasedAligner(config)
result = aligner.align(input_img, template)

cv2.imwrite('aligned_strict_qc.jpg', result.aligned_image)

# Create red overlay diff
red_overlay = create_red_overlay_diff(
    template,
    result.aligned_image,
    threshold=30,
    alpha=0.6
)
cv2.imwrite('aligned_strict_qc_red_overlay.jpg', red_overlay)

print(f"[STRICT QC] Error: {result.reprojection_error:.2f}px, Inliers: {result.inlier_ratio:.1f}%")

# Optional simple pass/fail:
ok = (result.inlier_ratio > 50 and result.reprojection_error < 3)
print(f"[STRICT QC] PASS: {ok}")
# %%
