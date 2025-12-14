# %%
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


BASE_DIR = Path(__file__).resolve().parent
OCR_DIR = BASE_DIR / "batch_outputs" / "json_data"
TRUTH_DIR = BASE_DIR / "sample_form_true_data"
REPORT_PATH = BASE_DIR / "ocr_accuracy_report.txt"


def load_json(path: Path) -> Tuple[Optional[Any], Optional[str]]:
    if not path.exists():
        return None, "missing"
    if path.stat().st_size == 0:
        return None, "empty"
    try:
        return json.loads(path.read_text()), None
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        return None, f"invalid_json: {exc}"


def extract_value(raw: Any) -> Any:
    if isinstance(raw, dict) and "text" in raw:
        return raw.get("text")
    return raw


def to_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def compare_documents(truth: Dict[str, Any], ocr: Dict[str, Any]) -> Tuple[int, int, List[str]]:
    matches = 0
    total = 0
    mismatches: List[str] = []

    for key, truth_value in truth.items():
        total += 1
        observed_raw = extract_value(ocr.get(key)) if ocr is not None else "<missing>"
        truth_str = to_string(truth_value)
        observed_str = to_string(observed_raw)

        if observed_str == truth_str:
            matches += 1
        else:
            mismatches.append(f"{key}: expected={truth_str!r}, observed={observed_str!r}")

    return matches, total, mismatches


def build_report() -> str:
    overall_matches = 0
    overall_total = 0
    evaluated_docs = 0
    skipped_missing_or_empty = 0
    skipped_other = 0
    per_doc_sections: List[str] = []

    ocr_files = sorted(p for p in OCR_DIR.glob("*.json") if p.is_file())

    for ocr_path in ocr_files:
        truth_path = TRUTH_DIR / ocr_path.name
        truth_data, truth_err = load_json(truth_path)

        if truth_err in {"missing", "empty"}:
            skipped_missing_or_empty += 1
            continue
        if truth_err is not None:
            skipped_other += 1
            per_doc_sections.append(
                f"{ocr_path.name}: skipped due to truth error ({truth_err})"
            )
            continue

        ocr_data, ocr_err = load_json(ocr_path)
        if ocr_err is not None:
            skipped_other += 1
            per_doc_sections.append(
                f"{ocr_path.name}: skipped due to OCR error ({ocr_err})"
            )
            continue

        if not isinstance(truth_data, dict):
            skipped_other += 1
            per_doc_sections.append(
                f"{ocr_path.name}: skipped because truth is not an object"
            )
            continue
        if not isinstance(ocr_data, dict):
            skipped_other += 1
            per_doc_sections.append(
                f"{ocr_path.name}: skipped because OCR is not an object"
            )
            continue

        matches, total, mismatches = compare_documents(truth_data, ocr_data)
        evaluated_docs += 1
        overall_matches += matches
        overall_total += total

        accuracy = matches / total if total else 0.0
        section_lines = [
            f"{ocr_path.name}",
            f"  accuracy: {accuracy:.4f} ({matches}/{total})",
        ]
        if mismatches:
            section_lines.append("  mismatches:")
            section_lines.extend(f"    - {line}" for line in mismatches)
        per_doc_sections.append("\n".join(section_lines))

    overall_accuracy = overall_matches / overall_total if overall_total else 0.0

    header = [
        "OCR Accuracy Report",
        "===================",
        f"Overall accuracy: {overall_accuracy:.4f} ({overall_matches}/{overall_total})",
        f"Documents evaluated: {evaluated_docs}",
        f"Documents skipped (missing/empty truth): {skipped_missing_or_empty}",
        f"Documents skipped (other issues): {skipped_other}",
        "",
        "Per-document results",
        "--------------------",
    ]

    return "\n".join(header + per_doc_sections)


def write_report(report_text: str, destination: Path) -> None:
    destination.write_text(report_text)
    print(f"Report written to {destination}")


if __name__ == "__main__":
    report = build_report()
    write_report(report, REPORT_PATH)
    print(report)

# %%
