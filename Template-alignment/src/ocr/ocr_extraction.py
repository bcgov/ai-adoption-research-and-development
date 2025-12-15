"""
Fast OCR Extraction using PaddleOCR (CORRECT API)
"""

import cv2
import numpy as np
import json
from typing import Dict, List, Tuple
import csv


def load_extraction_zones(csv_path: str, field_type: str = None) -> List[Dict]:
    """
    Load extraction zones from CSV file.

    Args:
        csv_path: Path to CSV file
        field_type: Optional filter - only load zones of this type ('text', 'checkbox', etc.)
                   If None, loads all zones.
    """
    zones = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Filter by type if specified
            if field_type is not None and 'type' in row:
                if row['type'] != field_type:
                    continue

            zone = {
                'name': row['label_name'],
                'bbox': {
                    'x': int(row['bbox_x']),
                    'y': int(row['bbox_y']),
                    'width': int(row['bbox_width']),
                    'height': int(row['bbox_height'])
                }
            }
            zones.append(zone)
    return zones


def extract_roi(image: np.ndarray, bbox: Dict, padding: int = 0) -> np.ndarray:
    """
    Extract region of interest from image with optional padding.
    
    Args:
        image: Source image
        bbox: Dict with x, y, width, height
        padding: Padding in pixels to add around ROI (default: 0)
    
    Returns:
        Extracted ROI with padding applied (clamped to image bounds)
    """
    x = bbox['x']
    y = bbox['y']
    w = bbox['width']
    h = bbox['height']
    
    img_h, img_w = image.shape[:2]
    
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
    
    roi = image[y_padded:y_padded+h_padded, x_padded:x_padded+w_padded]
    return roi


def preprocess_roi(roi: np.ndarray) -> np.ndarray:
    """Preprocess ROI for better OCR results."""
    if len(roi.shape) == 3:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    else:
        gray = roi

    # CLAHE for contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # Convert back to 3-channel format for PaddleOCR compatibility
    enhanced_3ch = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)

    return enhanced_3ch


class FastOCRExtractor:
    """
    Fast OCR extractor using PaddleOCR.
    
    Based on official PaddleOCR documentation:
    https://github.com/PaddlePaddle/PaddleOCR
    """
    
    def __init__(
        self,
        lang: str = 'en',
        verbose: bool = True,
        det_db_thresh: float = None,
        det_db_box_thresh: float = None,
        det_db_unclip_ratio: float = None,
        det_limit_side_len: int = None,
        det_limit_type: str = 'max',
        use_doc_orientation_classify: bool = False,
        use_doc_unwarping: bool = False,
        use_textline_orientation: bool = True,
        use_angle_cls: bool = None,  # deprecated in PaddleOCR 3.x; prefer textline orientation
        use_doc_preprocessor: bool = None,  # optional; only on newer versions
    ):
        """
        Initialize PaddleOCR extractor.
        
        Args:
            lang: Language code ('en', 'ch', 'fr', 'german', 'korean', 'japan')
            verbose: Print progress
            det_db_thresh: Optional DB detector threshold override (lower = more sensitive)
            det_db_box_thresh: Optional DB box filter threshold override
            det_db_unclip_ratio: Optional DB box expansion ratio
            det_limit_side_len: Optional detector input size limit
        """
        try:
            from paddleocr import PaddleOCR
        except ImportError:
            raise ImportError(
                "PaddleOCR not installed. Run:\n"
                "pip install paddleocr"
            )
        
        self.verbose = verbose
        
        if self.verbose:
            print("[OCR] Initializing PaddleOCR...")
            print(f"      Language: {lang}")
        
        ocr_kwargs = {}
        if det_db_thresh is not None:
            ocr_kwargs["det_db_thresh"] = det_db_thresh
        if det_db_box_thresh is not None:
            ocr_kwargs["det_db_box_thresh"] = det_db_box_thresh
        if det_db_unclip_ratio is not None:
            ocr_kwargs["det_db_unclip_ratio"] = det_db_unclip_ratio
        if det_limit_side_len is not None:
            ocr_kwargs["det_limit_side_len"] = det_limit_side_len
        if det_limit_type is not None:
            ocr_kwargs["det_limit_type"] = det_limit_type
        if use_doc_orientation_classify is not None:
            ocr_kwargs["use_doc_orientation_classify"] = use_doc_orientation_classify
        if use_doc_unwarping is not None:
            ocr_kwargs["use_doc_unwarping"] = use_doc_unwarping
        if use_textline_orientation is not None:
            ocr_kwargs["use_textline_orientation"] = use_textline_orientation
        if use_angle_cls is not None:
            ocr_kwargs["use_angle_cls"] = use_angle_cls
        if use_doc_preprocessor is not None:
            ocr_kwargs["use_doc_preprocessor"] = use_doc_preprocessor
            
        # CORRECT API - Based on official docs
        self.ocr = PaddleOCR(
            lang=lang,
            **ocr_kwargs,
            # Note: No show_log or use_gpu parameters in constructor
        )
        
        if self.verbose:
            print("[OCR] Ready!")
    
    def _parse_ocr_result(self, ocr_result) -> Tuple[List[str], List[float]]:
        """
        Parse PaddleX / PaddleOCR result object into texts and confidence scores.
        Handles both dict-like OCRResult objects and legacy attribute-based outputs.
        """
        texts: List[str] = []
        confidences: List[float] = []

        # Most recent PaddleX OCRResult behaves like a dict
        if isinstance(ocr_result, dict) or hasattr(ocr_result, "get"):
            texts = ocr_result.get("rec_texts") or ocr_result.get("texts") or []
            confidences = ocr_result.get("rec_scores") or ocr_result.get("scores") or []

        # Legacy attribute access (keep as fallback)
        if (not texts) and hasattr(ocr_result, "rec_texts"):
            texts = getattr(ocr_result, "rec_texts") or []
            confidences = getattr(ocr_result, "rec_scores", []) or []
        if (not texts) and hasattr(ocr_result, "texts"):
            texts = getattr(ocr_result, "texts") or []
            confidences = getattr(ocr_result, "scores", []) or []

        return texts, confidences

    def extract_text(self, image: np.ndarray, preprocess: bool = True) -> Tuple[str, float]:
        """
        Extract text from image region.

        Args:
            image: Image to extract text from
            preprocess: Apply preprocessing

        Returns:
            (extracted_text, confidence_score)
        """
        if preprocess:
            processed = preprocess_roi(image)
        else:
            processed = image

        # Ensure image is in correct format for PaddleOCR
        if len(processed.shape) == 2:
            # Convert grayscale to BGR
            processed = cv2.cvtColor(processed, cv2.COLOR_GRAY2BGR)
        elif len(processed.shape) == 3 and processed.shape[2] == 1:
            # Convert single-channel to BGR
            processed = cv2.cvtColor(processed, cv2.COLOR_GRAY2BGR)

        # Convert BGR to RGB (PaddleOCR might expect RGB)
        if len(processed.shape) == 3:
            processed = cv2.cvtColor(processed, cv2.COLOR_BGR2RGB)

        # Check minimum size requirements
        h, w = processed.shape[:2]
        if h < 10 or w < 10:
            if self.verbose:
                print(f"[DEBUG] Image too small for OCR: {w}x{h}")
            return "", 0.0

        # Run OCR (angle classification enabled in constructor)
        try:
            if self.verbose:
                print(f"[DEBUG] About to call self.ocr.ocr() on image shape {processed.shape}")

            result = self.ocr.ocr(processed)

            if self.verbose:
                print(f"[DEBUG] OCR call completed successfully")

        except Exception as e:
            if self.verbose:
                print(f"[DEBUG] OCR call failed with exception: {e}")
            return "", 0.0

        if not result or (isinstance(result, list) and len(result) == 0) or (isinstance(result, list) and len(result) > 0 and (result[0] is None or len(result[0]) == 0)):
            return "", 0.0

        # Handle PaddleOCR / PaddleX OCRResult format
        if not result or not isinstance(result, list):
            if self.verbose:
                print("[DEBUG] OCR result is empty or invalid")
            return "", 0.0

        ocr_result = result[0]
        texts, confidences = self._parse_ocr_result(ocr_result)

        if self.verbose:
            print(f"[DEBUG] Parsed OCR texts: {texts}")
            print(f"[DEBUG] Parsed OCR confidences: {confidences}")

        if not texts:
            return "", 0.0

        # Debug: print detected content
        if self.verbose:
            print(f"[DEBUG] OCR detected {len(texts)} text regions:")
            for i, (text, score) in enumerate(zip(texts, confidences)):
                print(f"         '{text}' (conf: {score:.2f})")

        # Keep all detected text without filtering
        cleaned_texts = [t.strip() for t in texts if t and t.strip()]
        cleaned_confidences = confidences[:len(cleaned_texts)]

        combined_text = " ".join(cleaned_texts)
        avg_confidence = np.mean(cleaned_confidences) if cleaned_confidences else 0.0
        
        return combined_text, float(avg_confidence)
    
    def extract_fields(
        self,
        image: np.ndarray,
        zones: List[Dict],
        preprocess: bool = True
    ) -> Dict[str, Dict]:
        """
        Extract all fields from image based on zones.
        
        Args:
            image: Aligned image
            zones: List of extraction zones
            preprocess: Apply preprocessing
            
        Returns:
            Dictionary mapping field names to extracted data
        """
        results = {}
        
        for zone in zones:
            name = zone['name']
            bbox = zone['bbox']
            
            if self.verbose:
                print(f"[OCR] Extracting '{name}'...")
            
            # Extract ROI
            roi = extract_roi(image, bbox)

            if roi.size == 0:
                results[name] = {
                    'text': '',
                    'confidence': 0.0,
                    'bbox': bbox,
                    'status': 'invalid_roi'
                }
                continue

            # DEBUG: Save ROI image for inspection
            import os
            debug_dir = 'debug_rois'
            if not os.path.exists(debug_dir):
                os.makedirs(debug_dir)
            roi_filename = f"{debug_dir}/{name}_roi.jpg"
            cv2.imwrite(roi_filename, roi)
            if self.verbose:
                print(f"      [DEBUG] Saved ROI to: {roi_filename} (shape: {roi.shape})")

            # DEBUG: Check ROI validity
            if self.verbose:
                # Check if ROI has content (not all same color)
                if len(roi.shape) == 3:
                    gray_check = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                else:
                    gray_check = roi
                unique_pixels = len(np.unique(gray_check))
                min_val, max_val = np.min(gray_check), np.max(gray_check)
                print(f"      [DEBUG] ROI stats - unique pixels: {unique_pixels}, range: [{min_val}, {max_val}]")

            # Extract text (only preprocessed path to reduce duplicate calls)
            if self.verbose:
                print(f"      [DEBUG] About to call extract_text (preprocess={preprocess})")

            text, confidence = self.extract_text(roi, preprocess=preprocess)

            if self.verbose:
                print(f"      [DEBUG] Using preprocessed result: '{text}' (conf: {confidence:.2f})")

            # DEBUG: Also save preprocessed image if preprocessing was enabled
            if preprocess and self.verbose:
                processed_roi = preprocess_roi(roi)
                processed_filename = f"{debug_dir}/{name}_processed.jpg"
                cv2.imwrite(processed_filename, processed_roi)
                print(f"      [DEBUG] Saved processed ROI to: {processed_filename}")
            text = text.strip()
            
            status = 'success' if confidence > 0.5 else 'low_confidence'
            
            if self.verbose:
                print(f"      Text: '{text}' (conf: {confidence:.2f})")
            
            results[name] = {
                'text': text,
                'confidence': confidence,
                'bbox': bbox,
                'status': status
            }
        
        return results


def visualize_extractions(
    image: np.ndarray,
    results: Dict[str, Dict],
    output_path: str = "extraction_visualization.jpg"
) -> np.ndarray:
    """Visualize extracted regions with bounding boxes."""
    vis = image.copy()
    
    for name, data in results.items():
        bbox = data['bbox']
        text = data['text']
        confidence = data['confidence']
        
        x, y, w, h = bbox['x'], bbox['y'], bbox['width'], bbox['height']
        
        # Color based on confidence
        if confidence > 0.8:
            color = (0, 255, 0)  # Green
        elif confidence > 0.5:
            color = (0, 165, 255)  # Orange
        else:
            color = (0, 0, 255)  # Red
        
        cv2.rectangle(vis, (x, y), (x + w, y + h), color, 2)
        
        # Label
        label = f"{name}: {text[:20]}" if len(text) > 20 else f"{name}: {text}"
        cv2.putText(vis, label, (x + 5, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    
    cv2.imwrite(output_path, vis)
    print(f"[VIS] Saved extraction visualization to: {output_path}")
    return vis
