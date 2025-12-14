# %%
import json
from pathlib import Path
from typing import Dict, List, Tuple

import cv2

from phase_1_alignment import FeatureBasedAligner, AlignmentConfig
from diff_visualization import create_red_overlay_diff
from debug_utils import debug_slice_ocr, build_paddle_ocr_debugger
from template_ocr_pipeline import (
    load_zones_from_template,
    build_union_mask,
    apply_mask,
    extract_polygon_roi,
    detect_checkboxes_from_template_image,
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
from ocr_extraction import FastOCRExtractor, visualize_extractions, extract_roi, preprocess_roi


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_TEMPLATE_IMAGE = BASE_DIR / "template.jpg"
DEFAULT_TEMPLATE_JSON = BASE_DIR / "template.json"

# ---------------------------------------------------------------------------
# Notebook-style configuration
# ---------------------------------------------------------------------------
INPUT_DIR = BASE_DIR / "sample_forms"        # change to your folder of inputs
OUTPUT_DIR = BASE_DIR / "batch_outputs"      # where json_data/debug_data will be written
TEMPLATE_IMAGE = DEFAULT_TEMPLATE_IMAGE      # or Path("/path/to/template.jpg")
TEMPLATE_JSON = DEFAULT_TEMPLATE_JSON        # or Path("/path/to/template.json")
EXTENSIONS = ("jpg", "jpeg", "png")          # tuple of extensions to process


def _safe_name(name: str) -> str:
    return name.replace("/", "_").replace("\\", "_")


def _load_template_assets(template_image_path: Path, template_json_path: Path) -> Tuple[Dict, Dict, Dict]:
    template_img = cv2.imread(str(template_image_path))
    if template_img is None:
        raise FileNotFoundError(f"Failed to read template image at '{template_image_path}'")
    polygon_zones, rectangle_zones, checkbox_boxes = load_zones_from_template(str(template_json_path))
    return template_img, polygon_zones, rectangle_zones, checkbox_boxes


def _build_aligner() -> FeatureBasedAligner:
    config = AlignmentConfig(
        feature_detector="ORB",
        max_features=5000,
        ratio_test_threshold=0.7,
        ransac_threshold=5.0,
        min_matches=10,
        verbose=True,
    )
    return FeatureBasedAligner(config)


def _build_extractor() -> Tuple[FastOCRExtractor, object]:
    extractor = FastOCRExtractor(
        lang="en",
        verbose=True,
        use_doc_orientation_classify=USE_DOC_ORIENTATION_CLASSIFY,
        use_doc_unwarping=USE_DOC_UNWARPING,
        use_textline_orientation=USE_TEXTLINE_ORIENTATION,
        det_db_thresh=DET_DB_THRESH,
        det_db_box_thresh=DET_DB_BOX_THRESH,
        det_db_unclip_ratio=DET_DB_UNCLIP_RATIO,
        det_limit_side_len=DET_LIMIT_SIDE_LEN,
        det_limit_type=DET_LIMIT_TYPE,
    )
    slice_debugger = build_paddle_ocr_debugger(
        lang="en",
        det_limit_side_len=DET_LIMIT_SIDE_LEN,
        det_limit_type=DET_LIMIT_TYPE,
        det_db_thresh=DET_DB_THRESH,
        det_db_box_thresh=DET_DB_BOX_THRESH,
        det_db_unclip_ratio=DET_DB_UNCLIP_RATIO,
        use_doc_orientation_classify=USE_DOC_ORIENTATION_CLASSIFY,
        use_doc_unwarping=USE_DOC_UNWARPING,
        use_textline_orientation=USE_TEXTLINE_ORIENTATION,
    )
    return extractor, slice_debugger


def process_single_document(
    input_image_path: Path,
    template_img,
    polygon_zones: List[Dict],
    rectangle_zones: List[Dict],
    checkbox_boxes: List[Dict],
    aligner: FeatureBasedAligner,
    extractor: FastOCRExtractor,
    slice_debugger,
    output_json_path: Path,
    debug_dir: Path,
    roi_padding: int = ROI_PADDING,
) -> Dict:
    debug_dir.mkdir(parents=True, exist_ok=True)
    slices_dir = debug_dir / "slices"
    slices_dir.mkdir(parents=True, exist_ok=True)

    input_img = cv2.imread(str(input_image_path))
    if input_img is None:
        raise FileNotFoundError(f"Failed to read input image at '{input_image_path}'")

    result = aligner.align(input_img, template_img)

    aligned_path = debug_dir / "aligned_default_orb.jpg"
    overlay_path = debug_dir / "aligned_default_orb_red_overlay.jpg"
    masked_path = debug_dir / "aligned_masked_for_ocr.png"
    extraction_vis_path = debug_dir / "extraction_visualization.jpg"
    slice_log_path = slices_dir / "slice_debug_log.txt"

    cv2.imwrite(str(aligned_path), result.aligned_image)
    red_overlay = create_red_overlay_diff(template_img, result.aligned_image, threshold=30, alpha=0.6)
    cv2.imwrite(str(overlay_path), red_overlay)

    union_mask = build_union_mask(result.aligned_image.shape, polygon_zones, rectangle_zones)
    masked_image = apply_mask(result.aligned_image, union_mask)
    cv2.imwrite(str(masked_path), masked_image)

    checkbox_results = detect_checkboxes_from_template_image(
        image=result.aligned_image,
        checkbox_boxes=checkbox_boxes,
        checked_threshold=0.15,
        verbose=False,
    )

    extracted_data: Dict[str, Dict] = {}

    for zone in polygon_zones:
        safe_name = _safe_name(zone["name"])
        roi = extract_polygon_roi(masked_image, zone["polygon"], padding=roi_padding)
        text, confidence = extractor.extract_text(roi, preprocess=True)
        extracted_data[zone["name"]] = {
            "text": text,
            "confidence": confidence,
            "bbox": zone["bbox"] if zone.get("bbox") else None,
        }
        cv2.imwrite(str(slices_dir / f"{safe_name}_roi.jpg"), roi)
        processed_roi = preprocess_roi(roi)
        cv2.imwrite(str(slices_dir / f"{safe_name}_processed.jpg"), processed_roi)
        debug_slice_ocr(
            processed_roi,
            slice_debugger,
            slices_dir,
            f"{safe_name}_processed",
            log_path=str(slice_log_path),
        )

    for zone in rectangle_zones:
        safe_name = _safe_name(zone["name"])
        roi = extract_roi(masked_image, zone["bbox"], padding=roi_padding)
        text, confidence = extractor.extract_text(roi, preprocess=True)
        extracted_data[zone["name"]] = {
            "text": text,
            "confidence": confidence,
            "bbox": zone["bbox"],
        }
        cv2.imwrite(str(slices_dir / f"{safe_name}_roi.jpg"), roi)
        processed_roi = preprocess_roi(roi)
        cv2.imwrite(str(slices_dir / f"{safe_name}_processed.jpg"), processed_roi)
        debug_slice_ocr(
            processed_roi,
            slice_debugger,
            slices_dir,
            f"{safe_name}_processed",
            log_path=str(slice_log_path),
        )

    combined_output = {**extracted_data, **checkbox_results}

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(combined_output, f, indent=2, ensure_ascii=False)

    visualize_extractions(result.aligned_image, extracted_data, str(extraction_vis_path))
    return combined_output


def run_batch(
    input_dir: Path,
    output_dir: Path,
    template_image_path: Path = DEFAULT_TEMPLATE_IMAGE,
    template_json_path: Path = DEFAULT_TEMPLATE_JSON,
    extensions: Tuple[str, ...] = ("jpg", "jpeg", "png"),
) -> None:
    input_dir = input_dir.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    output_json_dir = output_dir / "json_data"
    output_debug_dir = output_dir / "debug_data"

    template_img, polygon_zones, rectangle_zones, checkbox_boxes = _load_template_assets(
        template_image_path, template_json_path
    )
    aligner = _build_aligner()
    extractor, slice_debugger = _build_extractor()

    image_paths: List[Path] = []
    for ext in extensions:
        image_paths.extend(sorted(input_dir.glob(f"*.{ext}")))
    image_paths = sorted(set(image_paths))

    if not image_paths:
        raise FileNotFoundError(
            f"No input images found in '{input_dir}' for extensions: {', '.join(extensions)}"
        )

    print(f"[BATCH] Found {len(image_paths)} images in {input_dir}")
    successes, failures = 0, 0
    for img_path in image_paths:
        stem = img_path.stem
        json_path = output_json_dir / f"{stem}.json"
        debug_dir = output_debug_dir / stem
        try:
            print(f"[BATCH] Processing {img_path.name} -> {debug_dir}")
            process_single_document(
                input_image_path=img_path,
                template_img=template_img,
                polygon_zones=polygon_zones,
                rectangle_zones=rectangle_zones,
                checkbox_boxes=checkbox_boxes,
                aligner=aligner,
                extractor=extractor,
                slice_debugger=slice_debugger,
                output_json_path=json_path,
                debug_dir=debug_dir,
                roi_padding=ROI_PADDING,
            )
            successes += 1
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"[BATCH][ERROR] {img_path.name}: {exc}")

    print(
        f"[BATCH] Completed. Successes: {successes}, Failures: {failures}. "
        f"JSON in '{output_json_dir}', debug artifacts in '{output_debug_dir}'."
    )

run_batch(
    input_dir=Path(INPUT_DIR),
    output_dir=Path(OUTPUT_DIR),
    template_image_path=Path(TEMPLATE_IMAGE),
    template_json_path=Path(TEMPLATE_JSON),
    extensions=tuple(EXTENSIONS),
)

# %%
