"""Detection module for checkboxes and other form elements."""

from .checkbox_detection import SimpleCheckboxDetector, detect_checkboxes_from_csv

__all__ = ["SimpleCheckboxDetector", "detect_checkboxes_from_csv"]
