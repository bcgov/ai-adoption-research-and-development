"""Template loading utilities for parsing template JSON files."""

import json
from typing import Dict, List, Tuple


def load_template(template_path: str) -> Dict:
    """Load template JSON file."""
    with open(template_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_zones_from_template(template_path: str) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """
    Load zones from template.json grouped by type:
    - polygon_zones: text fields with segmentation
    - rectangle_zones: text fields with only bbox
    - checkbox_boxes: checkbox fields (by name prefix)
    """
    data = load_template(template_path)
    id_to_name = {cat["id"]: cat["name"] for cat in data.get("categories", [])}

    polygon_zones: List[Dict] = []
    rectangle_zones: List[Dict] = []
    checkbox_boxes: List[Dict] = []

    for ann in data.get("annotations", []):
        name = id_to_name.get(ann.get("category_id"))
        if not name:
            continue

        bbox = ann.get("bbox")
        seg = ann.get("segmentation")

        # Normalize bbox
        bbox_dict = None
        if bbox and len(bbox) == 4:
            x, y, w, h = bbox
            bbox_dict = {
                "x": int(round(x)),
                "y": int(round(y)),
                "width": int(round(w)),
                "height": int(round(h)),
            }

        if name.startswith("checkbox"):
            # Checkbox category
            if bbox_dict:
                checkbox_boxes.append({"name": name, "bbox": bbox_dict})
            continue

        # Text fields
        if seg and isinstance(seg, list) and seg[0]:
            coords = seg[0]
            if len(coords) >= 6:
                polygon = [(int(round(coords[i])), int(round(coords[i + 1]))) for i in range(0, len(coords), 2)]
                polygon_zones.append({"name": name, "polygon": polygon, "bbox": bbox_dict})
            continue

        # Rectangle text zones (no segmentation)
        if bbox_dict:
            rectangle_zones.append({"name": name, "bbox": bbox_dict})

    return polygon_zones, rectangle_zones, checkbox_boxes
