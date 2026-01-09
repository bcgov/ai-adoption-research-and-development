"""Common utility functions."""

import json
import os
from pathlib import Path
from typing import Any

import cv2
import numpy as np


def get_project_root() -> Path:
    """Get the project root directory."""
    current = Path(__file__).parent
    while current.parent != current:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    raise RuntimeError("Could not find project root (no pyproject.toml found)")


def ensure_dir(path: Path | str) -> Path:
    """Ensure a directory exists, creating it if necessary."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_image(path: Path | str) -> np.ndarray:
    """Load an image from disk."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    image = cv2.imread(str(path))
    if image is None:
        raise ValueError(f"Failed to load image: {path}")
    return image


def save_image(image: np.ndarray, path: Path | str) -> Path:
    """Save an image to disk."""
    path = Path(path)
    ensure_dir(path.parent)
    cv2.imwrite(str(path), image)
    return path


def load_json(path: Path | str) -> dict[str, Any]:
    """Load JSON from a file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: dict[str, Any], path: Path | str, indent: int = 2) -> Path:
    """Save data as JSON to a file."""
    path = Path(path)
    ensure_dir(path.parent)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)
    return path


def get_image_dimensions(image: np.ndarray) -> tuple[int, int]:
    """Get image dimensions (width, height)."""
    height, width = image.shape[:2]
    return width, height


def normalize_bbox(
    bbox: dict[str, float], page_width: float, page_height: float
) -> list[float]:
    """
    Convert pixel bbox to normalized coordinates (0-1 scale).

    Azure DI expects 8 coordinates: [x1,y1, x2,y1, x2,y2, x1,y2] (clockwise from top-left)

    Args:
        bbox: Dict with x, y, width, height in pixels
        page_width: Page width in pixels
        page_height: Page height in pixels

    Returns:
        List of 8 normalized coordinates
    """
    x = bbox["x"] / page_width
    y = bbox["y"] / page_height
    w = bbox["width"] / page_width
    h = bbox["height"] / page_height

    return [
        x, y,           # top-left
        x + w, y,       # top-right
        x + w, y + h,   # bottom-right
        x, y + h,       # bottom-left
    ]


def normalize_polygon(
    polygon: list[float], page_width: float, page_height: float
) -> list[float]:
    """
    Normalize polygon coordinates to 0-1 scale.

    Args:
        polygon: Flat list of [x1, y1, x2, y2, ...] coordinates in pixels
        page_width: Page width in pixels
        page_height: Page height in pixels

    Returns:
        Normalized polygon coordinates
    """
    normalized = []
    for i in range(0, len(polygon), 2):
        normalized.append(polygon[i] / page_width)
        normalized.append(polygon[i + 1] / page_height)
    return normalized


def polygon_to_bbox(polygon: list[float]) -> dict[str, float]:
    """Convert a polygon to a bounding box."""
    xs = polygon[0::2]
    ys = polygon[1::2]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    return {
        "x": x_min,
        "y": y_min,
        "width": x_max - x_min,
        "height": y_max - y_min,
    }


def print_progress(current: int, total: int, prefix: str = "", suffix: str = "") -> None:
    """Print a simple progress indicator."""
    percent = (current / total) * 100
    print(f"\r{prefix} [{current}/{total}] {percent:.1f}% {suffix}", end="", flush=True)
    if current == total:
        print()  # New line at completion
