"""Template processing utilities for loading and processing template definitions."""

from .template_loader import (
    load_template,
    load_zones_from_template,
)
from .template_processing import (
    build_union_mask,
    apply_mask,
    extract_polygon_roi,
    extract_checkbox_roi,
    save_checkbox_rois,
    detect_checkboxes_from_template_image,
    subtract_template_from_aligned,
)
from .config import (
    ROI_PADDING,
    DET_DB_THRESH,
    DET_DB_BOX_THRESH,
    DET_DB_UNCLIP_RATIO,
    DET_LIMIT_SIDE_LEN,
    DET_LIMIT_TYPE,
    USE_DOC_ORIENTATION_CLASSIFY,
    USE_DOC_UNWARPING,
    USE_TEXTLINE_ORIENTATION,
)

__all__ = [
    "load_template",
    "load_zones_from_template",
    "build_union_mask",
    "apply_mask",
    "extract_polygon_roi",
    "extract_checkbox_roi",
    "save_checkbox_rois",
    "detect_checkboxes_from_template_image",
    "subtract_template_from_aligned",
    "ROI_PADDING",
    "DET_DB_THRESH",
    "DET_DB_BOX_THRESH",
    "DET_DB_UNCLIP_RATIO",
    "DET_LIMIT_SIDE_LEN",
    "DET_LIMIT_TYPE",
    "USE_DOC_ORIENTATION_CLASSIFY",
    "USE_DOC_UNWARPING",
    "USE_TEXTLINE_ORIENTATION",
]
