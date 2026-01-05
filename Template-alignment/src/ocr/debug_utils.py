import os
from typing import List, Tuple, Optional

import cv2
import numpy as np
from paddleocr import PaddleOCR


def _log_lines(log_path: str, lines: List[str]) -> None:
    if not log_path:
        return
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        for line in lines:
            f.write(line.rstrip() + "\n")


def _collect_boxes(obj, path: str = "root") -> Tuple[List[np.ndarray], List[str], List[float]]:
    """Recursively collect candidate polygons/boxes from nested PaddleOCR results."""
    boxes_local: List[np.ndarray] = []
    texts_local: List[str] = []
    confs_local: List[float] = []
    key_names = ["det_polygons", "boxes", "polys", "points", "dt_polys", "dt_boxes"]

    if isinstance(obj, dict):
        for k in key_names:
            if k in obj and obj[k] is not None:
                candidate = obj[k]
                if isinstance(candidate, (list, tuple, np.ndarray)):
                    boxes_local.extend(candidate)
                    texts_local = obj.get("rec_texts") or obj.get("texts") or obj.get("label") or []
                    confs_local = obj.get("rec_scores") or obj.get("scores") or []
        for k, v in obj.items():
            b, t, c = _collect_boxes(v, path=f"{path}.{k}")
            if b:
                boxes_local.extend(b)
                texts_local.extend(t)
                confs_local.extend(c)
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            b, t, c = _collect_boxes(item, path=f"{path}[{idx}]")
            if b:
                boxes_local.extend(b)
                texts_local.extend(t)
                confs_local.extend(c)
    return boxes_local, texts_local, confs_local


def build_paddle_ocr_debugger(**kwargs) -> PaddleOCR:
    """Factory to build a PaddleOCR instance for debug-only runs."""
    return PaddleOCR(**kwargs)


def debug_slice_ocr(
    slice_img,
    paddle_ocr: PaddleOCR,
    output_dir: str,
    base_name: str,
    log_path: Optional[str] = None,
    rotate_from_preprocessor: bool = True,
) -> None:
    """
    Run PaddleOCR on a slice, save detection boxes visualization, and log results.

    Args:
        slice_img: BGR image (numpy array).
        paddle_ocr: Initialized PaddleOCR instance (reuse for speed).
        output_dir: Directory to store debug images.
        base_name: Base name for saved artifacts.
        log_path: Optional text log path.
        rotate_from_preprocessor: If true, rotate visualization according to
            doc_preprocessor angle metadata when present.
    """
    os.makedirs(output_dir, exist_ok=True)
    slice_rgb = cv2.cvtColor(slice_img, cv2.COLOR_BGR2RGB)
    result = paddle_ocr.ocr(slice_rgb)

    # Save doc_preprocessor images if present
    if isinstance(result, list) and len(result) > 0 and isinstance(result[0], dict):
        dpr = result[0].get("doc_preprocessor_res") or {}
        for key, fname in [
            ("input_img", "doc_preproc_input.jpg"),
            ("rot_img", "doc_preproc_rot.jpg"),
            ("output_img", "doc_preproc_output.jpg"),
        ]:
            img = dpr.get(key)
            if img is not None:
                out_path = os.path.join(output_dir, f"{base_name}_{fname}")
                cv2.imwrite(out_path, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
                _log_lines(log_path, [f"[DOC_PREPROC] Saved {key} -> {out_path} (shape={img.shape})"])

    debug_img = slice_img.copy()
    if rotate_from_preprocessor and isinstance(result, list) and len(result) > 0 and isinstance(result[0], dict):
        angle = (result[0].get("doc_preprocessor_res") or {}).get("angle")
        if angle in (90, 180, 270):
            rotate_code = {
                90: cv2.ROTATE_90_CLOCKWISE,
                180: cv2.ROTATE_180,
                270: cv2.ROTATE_90_COUNTERCLOCKWISE,
            }.get(angle)
            if rotate_code is not None:
                debug_img = cv2.rotate(slice_img.copy(), rotate_code)
                _log_lines(log_path, [f"[DOC_PREPROC] Rotated slice by {angle} degrees for visualization"])

    boxes, texts, confs = [], [], []
    if result:
        if isinstance(result, list) and len(result) > 0 and isinstance(result[0], list):
            items = result[0]
            for item in items:
                if not item:
                    continue
                box = item[0] if len(item) > 0 else None
                text_info = item[1] if len(item) > 1 else ("", 0.0)
                boxes.append(box)
                if isinstance(text_info, (list, tuple)) and len(text_info) >= 2:
                    texts.append(text_info[0])
                    confs.append(text_info[1])
                elif isinstance(text_info, (list, tuple)) and len(text_info) == 1:
                    texts.append(text_info[0])
                    confs.append(0.0)
                else:
                    texts.append(str(text_info) if text_info else "")
                    confs.append(0.0)
        else:
            boxes, texts, confs = _collect_boxes(result)

    # Fallback: detection-only predict
    if len(boxes) == 0:
        try:
            det_only = paddle_ocr.predict(slice_rgb, det=True, rec=False)
            boxes, texts, confs = _collect_boxes(det_only)
            _log_lines(log_path, ["[DEBUG] Fallback detect-only succeeded"])
        except Exception as e:
            _log_lines(log_path, [f"[DEBUG] predict(det-only) failed: {e}"])

    lines = [f"[DEBUG] Detected {len(boxes)} text boxes for {base_name}"]
    for idx, box in enumerate(boxes):
        try:
            if isinstance(box, np.ndarray):
                box_array = box.astype(np.int32)
            elif isinstance(box, (list, tuple)):
                box_array = np.array(box, dtype=np.float32).astype(np.int32)
            else:
                lines.append(f"[WARN] Box {idx} unexpected type {type(box)}")
                continue

            if box_array.ndim == 2 and box_array.shape == (4, 2):
                points = box_array.reshape((-1, 1, 2))
            elif box_array.ndim == 3 and box_array.shape[1:] == (2,):
                points = box_array.reshape((-1, 1, 2))
            else:
                points = box_array.reshape((-1, 1, 2))

            cv2.polylines(debug_img, [points], True, (0, 255, 0), 2)
            cv2.putText(debug_img, str(idx), tuple(points[0][0]), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

            text_val = texts[idx] if idx < len(texts) else ""
            conf_val = confs[idx] if idx < len(confs) else 0.0
            lines.append(f"  Box {idx}: {box_array.tolist()} -> '{text_val}' (conf: {conf_val:.2f})")
        except Exception as e:
            lines.append(f"[ERROR] Failed to process box {idx}: {e}")
            continue

    out_path = os.path.join(output_dir, f"{base_name}_detection_boxes.jpg")
    cv2.imwrite(out_path, debug_img)
    lines.append(f"[SAVED] Detection boxes visualization: {out_path}")
    _log_lines(log_path, lines)
