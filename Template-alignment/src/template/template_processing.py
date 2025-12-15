"""Template processing utilities for mask creation and ROI extraction."""

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
    """Detect checkboxes from template-defined boxes."""
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
