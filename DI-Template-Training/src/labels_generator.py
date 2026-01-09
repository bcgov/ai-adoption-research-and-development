"""Generate fields.json and .labels.json files for Azure DI training."""

from pathlib import Path
from typing import Any, Optional

from shapely.geometry import Polygon, box

from .utils import load_json, save_json, normalize_bbox, polygon_to_bbox, print_progress
from .ocr_generator import extract_words_from_ocr, extract_selection_marks_from_ocr, get_page_dimensions


# Field type mapping based on field names
FIELD_TYPE_RULES = [
    # Checkbox fields
    (lambda name: name.startswith("checkbox_"), {"type": "selectionMark"}),
    # Date fields
    (lambda name: name in ("date", "spouse_date"), {"type": "date"}),
    # Income/number fields
    (lambda name: "income" in name, {"type": "number"}),
    # Signature fields (treated as region)
    (lambda name: "signature" in name, {"type": "signature"}),
    # Default: string
    (lambda name: True, {"type": "string"}),
]


def get_field_type(field_name: str) -> dict[str, str]:
    """Get Azure DI field type for a field name."""
    for rule_fn, field_type in FIELD_TYPE_RULES:
        if rule_fn(field_name):
            return field_type
    return {"type": "string"}


def generate_fields_json(
    categories: dict[int, str],
    output_path: Path | str,
    exclude_checkboxes: bool = False,
) -> dict[str, Any]:
    """
    Generate fields.json from template categories.

    Args:
        categories: Dict mapping category_id to field name
        output_path: Path for output JSON
        exclude_checkboxes: Whether to exclude checkbox fields

    Returns:
        The fields.json data with fields as a dictionary (field_name -> field_type_info)
    """
    fields = {}

    for cat_id, name in sorted(categories.items(), key=lambda x: x[0]):
        if exclude_checkboxes and name.startswith("checkbox_"):
            continue

        field_type = get_field_type(name)
        # Store field type info without the name (name is the key)
        fields[name] = field_type

    fields_data = {"fields": fields}
    save_json(fields_data, output_path)

    return fields_data


def _polygon_from_coords(coords: list[float]) -> Polygon:
    """Create a Shapely Polygon from flat coordinate list."""
    points = [(coords[i], coords[i + 1]) for i in range(0, len(coords), 2)]
    if len(points) < 3:
        return None
    return Polygon(points)


def _bbox_to_polygon(bbox: dict[str, float]) -> Polygon:
    """Create a Shapely box from bbox dict."""
    return box(
        bbox["x"],
        bbox["y"],
        bbox["x"] + bbox["width"],
        bbox["y"] + bbox["height"],
    )


def _words_in_zone(
    words: list[dict],
    zone_polygon: Polygon,
    min_overlap: float = 0.3,
) -> list[dict]:
    """
    Find words that overlap with a zone polygon.

    Args:
        words: List of word dicts with bbox
        zone_polygon: Shapely Polygon of the zone
        min_overlap: Minimum intersection ratio to consider a match

    Returns:
        List of matching words
    """
    matching = []

    for word in words:
        if "bbox" not in word:
            continue

        word_poly = _bbox_to_polygon(word["bbox"])

        try:
            intersection = zone_polygon.intersection(word_poly)
            word_area = word_poly.area

            if word_area > 0:
                overlap_ratio = intersection.area / word_area
                if overlap_ratio >= min_overlap:
                    matching.append(word)
        except Exception:
            # Skip invalid geometries
            continue

    return matching


def _selection_mark_in_zone(
    selection_marks: list[dict],
    zone_polygon: Polygon,
    min_overlap: float = 0.5,
) -> Optional[dict]:
    """
    Find the selection mark that overlaps with a zone polygon.

    Args:
        selection_marks: List of selection mark dicts with bbox
        zone_polygon: Shapely Polygon of the zone
        min_overlap: Minimum intersection ratio to consider a match

    Returns:
        The best matching selection mark, or None if no match
    """
    best_match = None
    best_overlap = 0

    for mark in selection_marks:
        if "bbox" not in mark:
            continue

        mark_poly = _bbox_to_polygon(mark["bbox"])

        try:
            intersection = zone_polygon.intersection(mark_poly)
            mark_area = mark_poly.area

            if mark_area > 0:
                overlap_ratio = intersection.area / mark_area
                if overlap_ratio >= min_overlap and overlap_ratio > best_overlap:
                    best_overlap = overlap_ratio
                    best_match = mark
        except Exception:
            # Skip invalid geometries
            continue

    return best_match


def generate_labels_json(
    image_name: str,
    ocr_data: dict[str, Any],
    zones: dict[str, Any],
    output_path: Path | str,
) -> dict[str, Any]:
    """
    Generate .labels.json for a single image.

    Args:
        image_name: Name of the image file
        ocr_data: OCR JSON data for the image
        zones: Template zones dict from load_template_zones()
        output_path: Path for output JSON

    Returns:
        The labels.json data
    """
    # Extract words and selection marks from OCR
    words = extract_words_from_ocr(ocr_data)
    selection_marks = extract_selection_marks_from_ocr(ocr_data)
    page_width, page_height = get_page_dimensions(ocr_data)

    labels = []

    # Process polygon zones
    for zone in zones.get("polygon_zones", []):
        zone_name = zone["name"]

        # Skip checkbox zones (handled differently)
        if zone_name.startswith("checkbox_"):
            continue

        # Create zone polygon
        zone_polygon = _polygon_from_coords(zone["polygon"])
        if zone_polygon is None:
            continue

        # Find words in zone
        matching_words = _words_in_zone(words, zone_polygon)

        if matching_words:
            # Sort words by reading order using Azure OCR's span offset
            # This is 100% reliable as it uses Azure's authoritative reading order
            # Fallback to coordinate-based sorting if span data is missing
            if all("span" in w for w in matching_words):
                matching_words.sort(key=lambda w: w["span"]["offset"])
            else:
                # Fallback: sort by coordinates with y-rounding for tilted text
                matching_words.sort(key=lambda w: (round(w["bbox"]["y"] / 20) * 20, w["bbox"]["x"]))

            # Concatenate text in sorted order
            text = " ".join(w["text"] for w in matching_words)

            # Build bounding boxes in the same sorted order
            bounding_boxes = []
            for word in matching_words:
                bbox = word["bbox"]
                norm_bbox = normalize_bbox(bbox, page_width, page_height)
                bounding_boxes.append(norm_bbox)

            label = {
                "label": zone_name,
                "value": [{
                    "page": matching_words[0].get("page", 1),
                    "text": text,
                    "polygons": bounding_boxes,
                }],
            }
            labels.append(label)

    # Process rectangle zones (non-checkbox)
    for zone in zones.get("rectangle_zones", []):
        zone_name = zone["name"]

        if "bbox" not in zone:
            continue

        zone_polygon = _bbox_to_polygon(zone["bbox"])
        matching_words = _words_in_zone(words, zone_polygon)

        if matching_words:
            # Sort words by reading order using Azure OCR's span offset
            # Fallback to coordinate-based sorting if span data is missing
            if all("span" in w for w in matching_words):
                matching_words.sort(key=lambda w: w["span"]["offset"])
            else:
                # Fallback: sort by coordinates with y-rounding for tilted text
                matching_words.sort(key=lambda w: (round(w["bbox"]["y"] / 20) * 20, w["bbox"]["x"]))
            text = " ".join(w["text"] for w in matching_words)

            bounding_boxes = []
            for word in matching_words:
                bbox = word["bbox"]
                norm_bbox = normalize_bbox(bbox, page_width, page_height)
                bounding_boxes.append(norm_bbox)

            label = {
                "label": zone_name,
                "value": [{
                    "page": matching_words[0].get("page", 1),
                    "text": text,
                    "polygons": bounding_boxes,
                }],
            }
            labels.append(label)

    # Process checkbox zones
    for zone in zones.get("checkbox_zones", []):
        zone_name = zone["name"]

        if "bbox" not in zone:
            continue

        # Find the selection mark that overlaps with this checkbox zone
        zone_polygon = _bbox_to_polygon(zone["bbox"])
        matching_mark = _selection_mark_in_zone(selection_marks, zone_polygon, min_overlap=0.5)

        if matching_mark:
            # Use the actual state from the OCR selection mark
            state = matching_mark.get("state", "unselected")

            # Use the selection mark's bounding box (more accurate than zone bbox)
            mark_bbox = matching_mark["bbox"]
            norm_bbox = normalize_bbox(mark_bbox, page_width, page_height)
        else:
            # No selection mark found - default to unselected with zone bbox
            state = "unselected"
            norm_bbox = normalize_bbox(zone["bbox"], page_width, page_height)

        label = {
            "label": zone_name,
            "value": [{
                "page": 1,
                "text": f":{state}:",
                "polygons": [norm_bbox],
            }],
        }
        labels.append(label)

    labels_data = {
        "document": image_name,
        "labels": labels,
    }

    save_json(labels_data, output_path)
    return labels_data


def generate_labels_batch(
    image_ocr_pairs: list[tuple[str, dict[str, Any]]],
    zones: dict[str, Any],
    output_dir: Path | str,
    verbose: bool = True,
) -> list[dict]:
    """
    Generate .labels.json files for multiple images.

    Args:
        image_ocr_pairs: List of (image_name, ocr_data) tuples
        zones: Template zones dict
        output_dir: Directory for output files
        verbose: Print progress

    Returns:
        List of results with status for each image
    """
    output_dir = Path(output_dir)
    results = []

    for i, (image_name, ocr_data) in enumerate(image_ocr_pairs):
        if verbose:
            print_progress(i + 1, len(image_ocr_pairs), "Generating labels")

        output_path = output_dir / f"{image_name}.labels.json"

        try:
            labels_data = generate_labels_json(image_name, ocr_data, zones, output_path)
            results.append({
                "image": image_name,
                "success": True,
                "output": str(output_path),
                "label_count": len(labels_data.get("labels", [])),
            })
        except Exception as e:
            results.append({
                "image": image_name,
                "success": False,
                "error": str(e),
            })

    return results


def validate_training_data(training_dir: Path | str) -> dict[str, Any]:
    """
    Validate training data directory has all required files.

    Args:
        training_dir: Directory containing training data

    Returns:
        Validation result dict
    """
    training_dir = Path(training_dir)

    issues = []

    # Check fields.json
    fields_json = training_dir / "fields.json"
    if not fields_json.exists():
        issues.append("Missing fields.json")

    # Check training samples
    images = list(training_dir.glob("*.jpg"))

    if len(images) < 5:
        issues.append(f"Only {len(images)} images found, minimum 5 required")

    # Check each image has OCR and labels
    for img in images:
        ocr_file = training_dir / f"{img.name}.ocr.json"
        labels_file = training_dir / f"{img.name}.labels.json"

        if not ocr_file.exists():
            issues.append(f"Missing OCR file: {ocr_file.name}")

        if not labels_file.exists():
            issues.append(f"Missing labels file: {labels_file.name}")

    return {
        "valid": len(issues) == 0,
        "image_count": len(images),
        "issues": issues,
        "training_dir": str(training_dir),
    }
