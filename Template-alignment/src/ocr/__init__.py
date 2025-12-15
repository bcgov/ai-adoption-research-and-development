"""OCR extraction module using PaddleOCR."""

from .ocr_extraction import (
    FastOCRExtractor,
    visualize_extractions,
    extract_roi,
    preprocess_roi,
    load_extraction_zones,
)
from .debug_utils import debug_slice_ocr, build_paddle_ocr_debugger

__all__ = [
    "FastOCRExtractor",
    "visualize_extractions",
    "extract_roi",
    "preprocess_roi",
    "load_extraction_zones",
    "debug_slice_ocr",
    "build_paddle_ocr_debugger",
]
