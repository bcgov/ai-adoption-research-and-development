"""
Simple Checkbox Detection - Just returns true/false + confidence
No grouping, no validation - pure extraction
"""

import cv2
import numpy as np
import pandas as pd
from typing import Dict, Tuple


class SimpleCheckboxDetector:
    """
    Detect checkbox state using pixel density.
    Returns: is_checked (bool) + confidence (float)
    """
    
    def __init__(self, 
                 checked_threshold: float = 0.15,
                 verbose: bool = True):
        """
        Args:
            checked_threshold: Density above this = checked (default 15%)
            verbose: Print debug info
        """
        self.checked_threshold = checked_threshold
        self.verbose = verbose
    
    def detect_state(self, checkbox_roi: np.ndarray) -> Tuple[bool, float]:
        """
        Detect if checkbox is checked.
        
        Returns:
            (is_checked: bool, confidence: float)
        """
        # Convert to grayscale
        if len(checkbox_roi.shape) == 3:
            gray = cv2.cvtColor(checkbox_roi, cv2.COLOR_BGR2GRAY)
        else:
            gray = checkbox_roi
        
        # Otsu's thresholding
        _, binary = cv2.threshold(
            gray, 
            0, 
            255, 
            cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )
        
        # Calculate pixel density
        total_pixels = binary.size
        dark_pixels = cv2.countNonZero(binary)
        density = dark_pixels / total_pixels
        
        # Determine state
        is_checked = density > self.checked_threshold
        
        # Calculate confidence
        if is_checked:
            # Higher density = higher confidence
            confidence = min(density / (self.checked_threshold * 2), 1.0)
        else:
            # Lower density = higher confidence
            confidence = max(1.0 - (density / self.checked_threshold), 0.0)
        
        if self.verbose:
            status = "✓ CHECKED" if is_checked else "☐ UNCHECKED"
            print(f"      {status} (density: {density:.3f}, conf: {confidence:.2f})")
        
        return is_checked, float(confidence)
    
    def extract_checkbox(self, 
                        image: np.ndarray, 
                        bbox: Dict,
                        name: str,
                        padding: int = 0) -> Dict:
        """
        Extract single checkbox from image.
        
        Args:
            image: Document image
            bbox: Dict with x, y, width, height
            name: Checkbox field name
            padding: Padding in pixels to add/subtract from bbox (can be negative to crop)
                    Positive values expand the box, negative values shrink it
            
        Returns:
            Dict with checkbox state and confidence
        """
        # Extract ROI with padding support
        x = bbox['x']
        y = bbox['y']
        w = bbox['width']
        h = bbox['height']
        
        # Apply padding (can be negative to crop)
        x_padded = x + padding
        y_padded = y + padding
        w_padded = w - (2 * padding)  # Subtract padding from both sides
        h_padded = h - (2 * padding)
        
        # Clamp to image bounds
        img_h, img_w = image.shape[:2]
        x_padded = max(0, min(x_padded, img_w - 1))
        y_padded = max(0, min(y_padded, img_h - 1))
        w_padded = max(1, min(w_padded, img_w - x_padded))
        h_padded = max(1, min(h_padded, img_h - y_padded))
        
        roi = image[y_padded:y_padded+h_padded, x_padded:x_padded+w_padded]
        
        if roi.size == 0:
            return {
                'name': name,
                'checked': False,
                'confidence': 0.0,
                'status': 'invalid_roi'
            }
        
        # Detect state
        is_checked, confidence = self.detect_state(roi)
        
        return {
            'name': name,
            'checked': is_checked,
            'confidence': confidence,
            'status': 'success'
        }


def detect_checkboxes_from_csv(
    image: np.ndarray,
    csv_path: str,
    checked_threshold: float = 0.15,
    verbose: bool = True
) -> Dict:
    """
    Detect all checkboxes from CSV using explicit type annotations.

    Uses the 'type' column to identify checkboxes:
    - Fields with type='checkbox' are processed as checkboxes
    - Other fields are ignored

    Args:
        image: Aligned document image
        csv_path: Path to CSV with bbox definitions and type column
        checked_threshold: Density threshold (0.10-0.25 typical)
        verbose: Print debug info

    Returns:
        Dict mapping checkbox names to {checked: bool, confidence: float}
    """
    # Load CSV
    df = pd.read_csv(csv_path)

    # Filter for explicit checkbox types
    if 'type' in df.columns:
        checkbox_df = df[df['type'] == 'checkbox'].copy()
    else:
        # Fallback to size-based detection if no type column exists
        checkbox_df = df[
            (df['bbox_width'] < 200) &
            (df['bbox_height'] < 200)
        ].copy()
    
    if len(checkbox_df) == 0:
        if verbose:
            print("[CHECKBOX] No checkboxes found (no boxes smaller than 200x200)")
        return {}
    
    if verbose:
        print(f"\n{'='*70}")
        print(f"CHECKBOX DETECTION")
        print(f"{'='*70}")
        print(f"[CHECKBOX] Found {len(checkbox_df)} checkbox fields")
    
    # Initialize detector
    detector = SimpleCheckboxDetector(
        checked_threshold=checked_threshold,
        verbose=verbose
    )
    
    # Extract all checkboxes
    results = {}
    
    for _, row in checkbox_df.iterrows():
        name = row['label_name']
        
        if verbose:
            print(f"\n[CHECKBOX] '{name}'")
        
        bbox = {
            'x': int(row['bbox_x']),
            'y': int(row['bbox_y']),
            'width': int(row['bbox_width']),
            'height': int(row['bbox_height'])
        }
        
        result = detector.extract_checkbox(image, bbox, name)
        
        results[name] = {
            'checked': result['checked'],
            'confidence': result['confidence']
        }
    
    if verbose:
        print(f"\n{'='*70}\n")
    
    return results
