# %%
"""Full template-driven checkbox and OCR pipeline extracted from the notebook's
default ORB example."""

import os
import cv2
import json
import numpy as np
from typing import List, Dict, Tuple
from phase_1_alignment import FeatureBasedAligner, AlignmentConfig
from diff_visualization import create_red_overlay_diff
import importlib
import ocr_extraction as ocr_extraction_module
from debug_utils import debug_slice_ocr, build_paddle_ocr_debugger

# Reload to ensure latest changes are used when running in notebooks
importlib.reload(ocr_extraction_module)

from ocr_extraction import (
    FastOCRExtractor,
    visualize_extractions,
    extract_roi,
    preprocess_roi,
)
from checkbox_detection import SimpleCheckboxDetector


TEMPLATE_PATH = "template.json"
# Configure ROI padding (adds margin around extraction zones to prevent edge clipping)
# Recommended: 10-20 pixels for handwritten text, 5-10 for printed text
ROI_PADDING = 15  # Adjust this value to add more/less padding around OCR zones
# OCR detector tuning (aligned to slice debug settings)
DET_DB_THRESH = 0.3            # Lower = more sensitive to faint text
DET_DB_BOX_THRESH = 0.5        # Stricter box filtering
DET_DB_UNCLIP_RATIO = 2.0      # Box expansion ratio (higher to reduce truncation)
DET_LIMIT_SIDE_LEN = 2000      # Input size limit (match slice test)
DET_LIMIT_TYPE = "max"
USE_DOC_ORIENTATION_CLASSIFY = False
USE_DOC_UNWARPING = False
USE_TEXTLINE_ORIENTATION = True
# Slice-level debug controls (notebook-friendly globals)
SAVE_SLICE_DEBUG = True
SLICE_DEBUG_DIR = "debug_slices"
SLICE_LOG_PATH = "debug_slices/slice_debug_log.txt"


def load_template(template_path: str) -> Dict:
    with open(template_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_zones_from_template(template_path: str) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """
    Load zones from template.json grouped by type:
    - polygon_zones: text fields with segmentation
    - rectangle_zones: text fields with only bbox
    - checkbox_boxes: checkbox fields (by name prefix)
    """
    data = load_template(template_path)
    id_to_name = {cat["id"]: cat["name"] for cat in data.get("categories", [])}

    polygon_zones: List[Dict] = []
    rectangle_zones: List[Dict] = []
    checkbox_boxes: List[Dict] = []

    for ann in data.get("annotations", []):
        name = id_to_name.get(ann.get("category_id"))
        if not name:
            continue

        bbox = ann.get("bbox")
        seg = ann.get("segmentation")

        # Normalize bbox
        bbox_dict = None
        if bbox and len(bbox) == 4:
            x, y, w, h = bbox
            bbox_dict = {
                "x": int(round(x)),
                "y": int(round(y)),
                "width": int(round(w)),
                "height": int(round(h)),
            }

        if name.startswith("checkbox"):
            # Checkbox category
            if bbox_dict:
                checkbox_boxes.append({"name": name, "bbox": bbox_dict})
            continue

        # Text fields
        if seg and isinstance(seg, list) and seg[0]:
            coords = seg[0]
            if len(coords) >= 6:
                polygon = [(int(round(coords[i])), int(round(coords[i + 1]))) for i in range(0, len(coords), 2)]
                polygon_zones.append({"name": name, "polygon": polygon, "bbox": bbox_dict})
            continue

        # Rectangle text zones (no segmentation)
        if bbox_dict:
            rectangle_zones.append({"name": name, "bbox": bbox_dict})

    return polygon_zones, rectangle_zones, checkbox_boxes


def build_union_mask(image_shape: Tuple[int, int, int], polygon_zones: List[Dict], rectangle_zones: List[Dict]) -> np.ndarray:
    """Create a binary mask with text polygons/rectangles filled (255) and background 0."""
    mask = np.zeros(image_shape[:2], dtype=np.uint8)
    # Polygons
    for zone in polygon_zones:
        poly = np.array(zone["polygon"], dtype=np.int32)
        cv2.fillPoly(mask, [poly], 255)
    # Rectangles as polygons
    for zone in rectangle_zones:
        b = zone["bbox"]
        rect_poly = np.array(
            [
                [b["x"], b["y"]],
                [b["x"] + b["width"], b["y"]],
                [b["x"] + b["width"], b["y"] + b["height"]],
                [b["x"], b["y"] + b["height"]],
            ],
            dtype=np.int32,
        )
        cv2.fillPoly(mask, [rect_poly], 255)
    return mask


def apply_mask(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Keep only masked regions; paint everything else white."""
    white_bg = np.full_like(image, 255)
    return np.where(mask[:, :, None] > 0, image, white_bg)


def save_transparent_mask(mask: np.ndarray, output_path: str) -> None:
    """
    Save a visualization where OCR areas are transparent and the rest white.
    """
    h, w = mask.shape
    alpha = np.where(mask > 0, 0, 255).astype(np.uint8)  # OCR regions transparent
    rgb = np.full((h, w, 3), 255, dtype=np.uint8)  # white background
    rgba = np.dstack([rgb, alpha])
    cv2.imwrite(output_path, rgba)


def extract_polygon_roi(image: np.ndarray, polygon: List[Tuple[int, int]], padding: int = 0) -> np.ndarray:
    """
    Extract text region using polygon mask (white background outside polygon).

    Args:
        image: Source image
        polygon: List of (x, y) coordinates defining the polygon
        padding: Padding in pixels to add around ROI (default: 0)

    Returns:
        Extracted ROI with polygon mask applied and padding added
    """
    mask = np.zeros(image.shape[:2], dtype=np.uint8)
    polygon_np = np.array(polygon, dtype=np.int32)
    cv2.fillPoly(mask, [polygon_np], 255)

    img_h, img_w = image.shape[:2]
    x, y, w, h = cv2.boundingRect(polygon_np)

    # Apply padding with clamping
    x_padded = max(0, x - padding)
    y_padded = max(0, y - padding)
    w_padded = min(w + 2 * padding, img_w - x_padded)
    h_padded = min(h + 2 * padding, img_h - y_padded)

    # Ensure we don't go out of bounds
    x_padded = max(0, min(x_padded, img_w - 1))
    y_padded = max(0, min(y_padded, img_h - 1))
    w_padded = min(w_padded, img_w - x_padded)
    h_padded = min(h_padded, img_h - y_padded)

    roi = image[y_padded : y_padded + h_padded, x_padded : x_padded + w_padded]
    roi_mask = mask[y_padded : y_padded + h_padded, x_padded : x_padded + w_padded]

    white_bg = np.ones_like(roi) * 255
    masked_roi = np.where(roi_mask[:, :, np.newaxis] > 0, roi, white_bg)
    return masked_roi


def detect_checkboxes_from_template_image(
    image: np.ndarray, checkbox_boxes: List[Dict], checked_threshold: float = 0.15, verbose: bool = True
) -> Dict:
    detector = SimpleCheckboxDetector(checked_threshold=checked_threshold, verbose=verbose)
    results = {}
    if verbose:
        print(f"\n[CHECKBOX] Processing {len(checkbox_boxes)} checkbox fields from template.json")
    for box in checkbox_boxes:
        name = box["name"]
        bbox = box["bbox"]
        if verbose:
            print(f"\n[CHECKBOX] '{name}'")
        result = detector.extract_checkbox(image, bbox, name)
        results[name] = {"checked": result["checked"], "confidence": result["confidence"]}
    if verbose:
        print(f"\n{'='*70}\n")
    return results


def run_template_ocr_pipeline():
    # Load your images
    template = cv2.imread("template.jpg")
    input_img = cv2.imread("input_document.jpg")

    # Configure and align
    config = AlignmentConfig(
        feature_detector="ORB",
        max_features=5000,
        ratio_test_threshold=0.7,
        ransac_threshold=5.0,
        min_matches=10,
        verbose=True,
    )

    aligner = FeatureBasedAligner(config)
    result = aligner.align(input_img, template)

    # Save outputs
    cv2.imwrite("aligned_default_orb.jpg", result.aligned_image)

    red_overlay = create_red_overlay_diff(template, result.aligned_image, threshold=30, alpha=0.6)
    cv2.imwrite("aligned_default_orb_red_overlay.jpg", red_overlay)

    print(f"[DEFAULT] Error: {result.reprojection_error:.2f}px, Inliers: {result.inlier_ratio:.1f}%")

    # ============================================================================
    # TEMPLATE-DRIVEN CHECKBOX + OCR USING POLYGON MASKS
    # ============================================================================

    # Load zones (polygons + rectangles) and checkbox boxes from template.json
    polygon_zones, rectangle_zones, checkbox_boxes = load_zones_from_template(TEMPLATE_PATH)

    print(
        f"\n[TEMPLATE] Loaded {len(polygon_zones)} polygon text zones, "
        f"{len(rectangle_zones)} rectangle text zones, "
        f"{len(checkbox_boxes)} checkbox boxes"
    )

    # Build and apply global mask for OCR (white everywhere, keep text zones)
    union_mask = build_union_mask(result.aligned_image.shape, polygon_zones, rectangle_zones)
    masked_image = apply_mask(result.aligned_image, union_mask)

    # Save masked visualization (white background, OCR regions transparent)
    cv2.imwrite("aligned_masked_for_ocr.png", masked_image)

    # Detect checkboxes from template-defined boxes
    checkbox_results = detect_checkboxes_from_template_image(
        image=result.aligned_image,
        checkbox_boxes=checkbox_boxes,
        checked_threshold=0.15,  # Adjust if needed (0.10-0.25 typical)
        verbose=True,
    )

    # Print checkbox results
    print("[CHECKBOX] Results:")
    for name, data in checkbox_results.items():
        icon = "☑" if data["checked"] else "☐"
        conf_icon = "✓" if data["confidence"] > 0.5 else "⚠"
        print(f"  {icon} {name:30s}: {data['checked']} (conf: {data['confidence']:.2f}) {conf_icon}")

    # ============================================================================
    # FAST OCR EXTRACTION (PaddleOCR) USING POLYGONAL MASKS
    # ============================================================================

    # Initialize FAST OCR extractor (aligned with slice debug settings)
    extractor = FastOCRExtractor(
        lang="en",
        verbose=True,
        use_doc_orientation_classify=USE_DOC_ORIENTATION_CLASSIFY,
        use_doc_unwarping=USE_DOC_UNWARPING,
        use_textline_orientation=USE_TEXTLINE_ORIENTATION,
        det_db_thresh=DET_DB_THRESH,
        det_db_box_thresh=DET_DB_BOX_THRESH,
        det_db_unclip_ratio=DET_DB_UNCLIP_RATIO,
        det_limit_side_len=DET_LIMIT_SIDE_LEN,
        det_limit_type=DET_LIMIT_TYPE,
    )

    debug_dir = SLICE_DEBUG_DIR
    os.makedirs(debug_dir, exist_ok=True)
    slice_debugger = None
    if SAVE_SLICE_DEBUG:
        slice_debugger = build_paddle_ocr_debugger(
            lang="en",
            det_limit_side_len=DET_LIMIT_SIDE_LEN,
            det_limit_type=DET_LIMIT_TYPE,
            det_db_thresh=DET_DB_THRESH,
            det_db_box_thresh=DET_DB_BOX_THRESH,
            det_db_unclip_ratio=DET_DB_UNCLIP_RATIO,
            use_doc_orientation_classify=USE_DOC_ORIENTATION_CLASSIFY,
            use_doc_unwarping=USE_DOC_UNWARPING,
            use_textline_orientation=USE_TEXTLINE_ORIENTATION,
        )

    extracted_data = {}

    # Polygon text zones
    print(f"\n[OCR] Extracting {len(polygon_zones)} polygon text fields (padding: {ROI_PADDING}px)")
    for zone in polygon_zones:
        roi = extract_polygon_roi(masked_image, zone["polygon"], padding=ROI_PADDING)
        text, confidence = extractor.extract_text(roi, preprocess=True)
        extracted_data[zone["name"]] = {
            "text": text,
            "confidence": confidence,
            "bbox": zone["bbox"] if zone.get("bbox") else None,
        }
        cv2.imwrite(f"{debug_dir}/{zone['name']}_roi.jpg", roi)
        processed_roi = preprocess_roi(roi)
        cv2.imwrite(f"{debug_dir}/{zone['name']}_processed.jpg", processed_roi)
        conf_icon = "✓" if confidence > 0.5 else "⚠"
        print(f"  {conf_icon} {zone['name']:25s}: '{text}' (conf: {confidence:.2f})")
        if SAVE_SLICE_DEBUG and slice_debugger is not None:
            debug_slice_ocr(
                processed_roi,
                slice_debugger,
                debug_dir,
                f"{zone['name']}_processed",
                log_path=SLICE_LOG_PATH,
            )

    # Rectangle text zones
    print(f"\n[OCR] Extracting {len(rectangle_zones)} rectangle text fields (padding: {ROI_PADDING}px)")
    for zone in rectangle_zones:
        roi = extract_roi(masked_image, zone["bbox"], padding=ROI_PADDING)
        text, confidence = extractor.extract_text(roi, preprocess=True)
        extracted_data[zone["name"]] = {
            "text": text,
            "confidence": confidence,
            "bbox": zone["bbox"],
        }
        cv2.imwrite(f"{debug_dir}/{zone['name']}_roi.jpg", roi)
        processed_roi = preprocess_roi(roi)
        cv2.imwrite(f"{debug_dir}/{zone['name']}_processed.jpg", processed_roi)
        conf_icon = "✓" if confidence > 0.5 else "⚠"
        print(f"  {conf_icon} {zone['name']:25s}: '{text}' (conf: {confidence:.2f})")
        if SAVE_SLICE_DEBUG and slice_debugger is not None:
            debug_slice_ocr(
                processed_roi,
                slice_debugger,
                debug_dir,
                f"{zone['name']}_processed",
                log_path=SLICE_LOG_PATH,
            )

    # Combine with checkbox results
    combined_output = {**extracted_data, **checkbox_results}

    # Save combined JSON
    with open("extracted_data.json", "w", encoding="utf-8") as f:
        json.dump(combined_output, f, indent=2, ensure_ascii=False)

    # Visualize OCR extractions (optional: still uses bbox rectangles; polygons not drawn)
    visualize_extractions(result.aligned_image, extracted_data, "extraction_visualization.jpg")

    print(f"\n[DONE] Saved to: extracted_data.json")
    return combined_output

if __name__ == "__main__":
    run_template_ocr_pipeline()

# %%
