"""Wrapper for Template-alignment code."""

import os
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np

from .utils import get_project_root, load_json


class AlignmentMode(Enum):
    """Available alignment modes."""
    DEFAULT = "default"           # Fast ORB
    HIGH_ACCURACY = "high_accuracy"  # SIFT
    DIFFICULT = "difficult"       # Relaxed SIFT
    STRICT_QC = "strict_qc"       # Strict SIFT


@dataclass
class AlignmentResult:
    """Result of image alignment."""
    aligned_image: np.ndarray
    success: bool
    reprojection_error: float
    inlier_ratio: float
    num_matches: int
    message: str = ""


def _get_template_alignment_path() -> Path:
    """Get path to Template-alignment project."""
    # Check environment variable first
    env_path = os.environ.get("TEMPLATE_ALIGNMENT_PATH")
    if env_path:
        path = Path(env_path)
        if path.exists():
            return path.resolve()

    # Default: sibling directory
    project_root = get_project_root()
    default_path = project_root.parent / "Template-alignment"
    if default_path.exists():
        return default_path.resolve()

    raise RuntimeError(
        "Template-alignment project not found. Set TEMPLATE_ALIGNMENT_PATH "
        "environment variable or ensure it exists at ../Template-alignment"
    )


def _ensure_template_alignment_imported():
    """Ensure Template-alignment src is in sys.path."""
    ta_path = _get_template_alignment_path()
    src_path = str(ta_path / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


def get_alignment_config(mode: AlignmentMode | str):
    """
    Get alignment configuration for the specified mode.

    Args:
        mode: AlignmentMode enum or string name

    Returns:
        AlignmentConfig from Template-alignment
    """
    _ensure_template_alignment_imported()
    from alignment.phase_1_alignment import AlignmentConfig

    if isinstance(mode, str):
        mode = AlignmentMode(mode)

    configs = {
        AlignmentMode.DEFAULT: AlignmentConfig(
            feature_detector="ORB",
            max_features=5000,
            ratio_test_threshold=0.7,
            ransac_threshold=5.0,
            min_matches=10,
            verbose=False,
        ),
        AlignmentMode.HIGH_ACCURACY: AlignmentConfig(
            feature_detector="SIFT",
            max_features=5000,
            ratio_test_threshold=0.7,
            ransac_threshold=5.0,
            min_matches=10,
            verbose=False,
        ),
        AlignmentMode.DIFFICULT: AlignmentConfig(
            feature_detector="SIFT",
            max_features=8000,
            ratio_test_threshold=0.8,
            ransac_threshold=7.0,
            min_matches=8,
            verbose=False,
        ),
        AlignmentMode.STRICT_QC: AlignmentConfig(
            feature_detector="SIFT",
            max_features=6000,
            ratio_test_threshold=0.65,
            ransac_threshold=3.0,
            min_matches=20,
            verbose=False,
        ),
    }

    return configs[mode]


def align_image_to_template(
    input_image: np.ndarray,
    template_image: np.ndarray,
    mode: AlignmentMode | str = AlignmentMode.HIGH_ACCURACY,
) -> AlignmentResult:
    """
    Align an input image to a template image.

    Args:
        input_image: Input image (BGR)
        template_image: Template image (BGR)
        mode: Alignment mode

    Returns:
        AlignmentResult with aligned image and metrics
    """
    _ensure_template_alignment_imported()
    from alignment.phase_1_alignment import FeatureBasedAligner

    config = get_alignment_config(mode)
    aligner = FeatureBasedAligner(config)

    try:
        result = aligner.align(input_image, template_image)
        return AlignmentResult(
            aligned_image=result.aligned_image,
            success=result.success,
            reprojection_error=result.reprojection_error,
            inlier_ratio=result.inlier_ratio,
            num_matches=result.num_matches,
            message="Alignment successful",
        )
    except Exception as e:
        # Return empty result on failure
        return AlignmentResult(
            aligned_image=input_image,  # Return original on failure
            success=False,
            reprojection_error=float("inf"),
            inlier_ratio=0.0,
            num_matches=0,
            message=f"Alignment failed: {str(e)}",
        )


def load_template_zones(template_json_path: Path | str) -> dict[str, Any]:
    """
    Load template zones from template.json (COCO format).

    Args:
        template_json_path: Path to template.json

    Returns:
        Dict with 'polygon_zones', 'rectangle_zones', 'checkbox_zones', 'categories'
    """
    template = load_json(template_json_path)

    # Build category lookup
    categories = {cat["id"]: cat["name"] for cat in template["categories"]}

    # Get image dimensions
    image_info = template["images"][0]
    width = image_info["width"]
    height = image_info["height"]

    polygon_zones = []
    rectangle_zones = []
    checkbox_zones = []

    for ann in template["annotations"]:
        cat_id = ann["category_id"]
        name = categories.get(cat_id, f"field_{cat_id}")

        zone = {
            "id": ann["id"],
            "name": name,
            "category_id": cat_id,
        }

        # Extract bbox
        if "bbox" in ann:
            bbox = ann["bbox"]
            zone["bbox"] = {
                "x": bbox[0],
                "y": bbox[1],
                "width": bbox[2],
                "height": bbox[3],
            }

        # Check if it has segmentation (polygon)
        if "segmentation" in ann and ann["segmentation"]:
            zone["polygon"] = ann["segmentation"][0]
            polygon_zones.append(zone)
        else:
            # Rectangle only - check if checkbox
            if name.startswith("checkbox_"):
                checkbox_zones.append(zone)
            else:
                rectangle_zones.append(zone)

    return {
        "polygon_zones": polygon_zones,
        "rectangle_zones": rectangle_zones,
        "checkbox_zones": checkbox_zones,
        "categories": categories,
        "image_width": width,
        "image_height": height,
    }


def get_template_paths() -> dict[str, Path]:
    """Get paths to template files in Template-alignment project."""
    ta_path = _get_template_alignment_path()
    return {
        "template_json": ta_path / "data" / "templates" / "template.json",
        "template_image": ta_path / "data" / "templates" / "template.jpg",
        "sample_forms": ta_path / "data" / "inputs" / "sample_forms",
    }
