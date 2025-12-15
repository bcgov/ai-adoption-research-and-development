"""
Alignment Difference Visualization Module

Provides red overlay visualization to show alignment quality by highlighting
differences between template and aligned images in red.
"""

import cv2
import numpy as np
from typing import Optional


def create_red_overlay_diff(
    template: np.ndarray,
    aligned: np.ndarray,
    threshold: int = 30,
    alpha: float = 0.6
) -> np.ndarray:
    """
    Create red overlay showing differences between template and aligned image.
    
    Differences above threshold are highlighted in red on top of the template.
    
    Args:
        template: Template image (BGR)
        aligned: Aligned image (BGR)
        threshold: Difference threshold (0-255). Higher = less sensitive
        alpha: Transparency of red overlay (0-1). Lower = more transparent
        
    Returns:
        Image with red overlay highlighting differences
    """
    # Ensure same size
    if template.shape != aligned.shape:
        aligned = cv2.resize(aligned, (template.shape[1], template.shape[0]))
    
    # Convert to grayscale for comparison
    gray_template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    gray_aligned = cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY)
    
    # Compute absolute difference
    diff = cv2.absdiff(gray_template, gray_aligned)
    
    # Threshold to get significant differences
    _, diff_mask = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)
    
    # Create red overlay
    overlay = template.copy()
    overlay[diff_mask > 0] = [0, 0, 255]  # Red (BGR)
    
    # Blend with original
    result = cv2.addWeighted(template, 1 - alpha, overlay, alpha, 0)
    
    # Add diff percentage text
    diff_percentage = (np.sum(diff_mask > 0) / diff_mask.size) * 100
    cv2.putText(
        result,
        f"Diff: {diff_percentage:.2f}%",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (0, 0, 255),
        2
    )
    
    return result
