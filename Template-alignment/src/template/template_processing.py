"""Template processing utilities for mask creation and ROI extraction."""

import os
import cv2
import numpy as np
from typing import List, Dict, Tuple

from ..detection.checkbox_detection import SimpleCheckboxDetector


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


def subtract_template_from_aligned(
    aligned_image: np.ndarray,
    template_image: np.ndarray,
    similarity_threshold: int = 15,
    bleed_pixels: int = 0,
    preserve_color: bool = True
) -> np.ndarray:
    """
    Subtract template structure from aligned document, leaving only user-entered content.
    
    Where template and aligned pixels are similar (within threshold), sets pixel to white.
    This removes form structure (boxes, lines) while preserving filled-in content.
    Optionally expands removed areas by a bleed amount to ensure clean removal.
    
    Args:
        aligned_image: Aligned document image with filled information (BGR)
        template_image: Blank template form image (BGR)
        similarity_threshold: Pixel difference threshold (0-255). 
                             Higher = more aggressive removal (removes pixels with diff < threshold).
                             Lower = less aggressive (only removes very similar pixels).
                             Typical range: 5-30 for most documents.
        bleed_pixels: Number of pixels to expand removed areas (default: 0). 
                     Uses morphological dilation to expand white areas.
        preserve_color: If True, preserves color of differences; if False, converts to grayscale
    
    Returns:
        BGR image with template structure removed (white where template matches)
    """
    # Ensure same dimensions
    if template_image.shape != aligned_image.shape:
        template_image = cv2.resize(template_image, (aligned_image.shape[1], aligned_image.shape[0]))
    
    # Convert to grayscale for comparison
    gray_template = cv2.cvtColor(template_image, cv2.COLOR_BGR2GRAY)
    gray_aligned = cv2.cvtColor(aligned_image, cv2.COLOR_BGR2GRAY)
    
    # Compute absolute difference
    diff = cv2.absdiff(gray_template, gray_aligned)
    
    # Create mask: where difference is small, template structure exists (set to white)
    # Threshold: if diff < threshold, it's template structure
    _, template_mask = cv2.threshold(diff, similarity_threshold, 255, cv2.THRESH_BINARY_INV)
    # template_mask is 255 where template matches (should be removed), 0 where content differs
    
    # Apply bleed: expand the white (removed) areas
    if bleed_pixels > 0:
        kernel_size = 2 * bleed_pixels + 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        template_mask = cv2.dilate(template_mask, kernel, iterations=1)
    
    # Create result: where mask is 255 (template structure), set to white; otherwise keep aligned
    result = aligned_image.copy()
    
    # Apply mask: set template structure areas to white
    white_bg = np.full_like(aligned_image, 255)
    result = np.where(template_mask[:, :, np.newaxis] > 0, white_bg, result)
    
    # If not preserving color, convert to grayscale and back to BGR
    if not preserve_color:
        gray_result = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
        result = cv2.cvtColor(gray_result, cv2.COLOR_GRAY2BGR)
    
    return result


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


def extract_checkbox_roi(image: np.ndarray, bbox: Dict, padding: int = 0) -> np.ndarray:
    """
    Extract a checkbox ROI with optional padding (positive expands, negative crops).
    """
    x = bbox["x"]
    y = bbox["y"]
    w = bbox["width"]
    h = bbox["height"]

    # Apply padding (can be negative to crop)
    x_padded = x + padding
    y_padded = y + padding
    w_padded = w - (2 * padding)
    h_padded = h - (2 * padding)

    # Clamp to image bounds
    img_h, img_w = image.shape[:2]
    x_padded = max(0, min(x_padded, img_w - 1))
    y_padded = max(0, min(y_padded, img_h - 1))
    w_padded = max(1, min(w_padded, img_w - x_padded))
    h_padded = max(1, min(h_padded, img_h - y_padded))

    roi = image[y_padded : y_padded + h_padded, x_padded : x_padded + w_padded]
    return roi


def save_checkbox_rois(
    image: np.ndarray,
    checkbox_boxes: List[Dict],
    checkbox_results: Dict,
    padding: int,
    output_dir: str,
) -> None:
    """
    Save checkbox ROIs (with padding applied) to a debug directory.

    Filenames include status and confidence for quick inspection.
    """
    os.makedirs(output_dir, exist_ok=True)

    for box in checkbox_boxes:
        name = box["name"]
        bbox = box["bbox"]

        roi = extract_checkbox_roi(image, bbox, padding=padding)
        if roi is None or roi.size == 0:
            continue

        cv2.imwrite(os.path.join(output_dir, f"{name}_checkbox.jpg"), roi)


def detect_checkboxes_from_template_image(
    image: np.ndarray, 
    checkbox_boxes: List[Dict], 
    checked_threshold: float = 0.15, 
    padding: int = 0,
    verbose: bool = True
) -> Dict:
    """
    Detect checkboxes from template-defined boxes.
    
    Args:
        image: Document image
        checkbox_boxes: List of checkbox box definitions from template.json
        checked_threshold: Density threshold for checked state (0.10-0.25 typical)
        padding: Padding in pixels to add/subtract from checkbox boxes (can be negative to crop).
                Positive values expand the box, negative values shrink it.
                Useful for cropping out visible box borders that interfere with detection.
        verbose: Print debug info
        
    Returns:
        Dict mapping checkbox names to {checked: bool, confidence: float}
    """
    detector = SimpleCheckboxDetector(checked_threshold=checked_threshold, verbose=verbose)
    results = {}
    if verbose:
        padding_str = f" (padding: {padding:+d}px)" if padding != 0 else ""
        print(f"\n[CHECKBOX] Processing {len(checkbox_boxes)} checkbox fields from template.json{padding_str}")
    for box in checkbox_boxes:
        name = box["name"]
        bbox = box["bbox"]
        if verbose:
            print(f"\n[CHECKBOX] '{name}'")
        result = detector.extract_checkbox(image, bbox, name, padding=padding)
        results[name] = {"checked": result["checked"], "confidence": result["confidence"]}
    if verbose:
        print(f"\n{'='*70}\n")
    return results
