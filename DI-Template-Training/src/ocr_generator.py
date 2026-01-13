"""Generate .ocr.json files using Azure Document Intelligence Layout API."""

import json
from pathlib import Path
from typing import Any, Optional

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult

from .utils import print_progress, save_json


def _capture_raw_response(response_holder: dict):
    """Create a callback to capture the raw API response."""
    def callback(raw_response, deserialized, headers):
        response_holder["raw"] = raw_response.http_response.body().decode("utf-8")
        return deserialized
    return callback


def generate_ocr_json(
    client: DocumentIntelligenceClient,
    image_path: Path | str,
    output_path: Optional[Path | str] = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """
    Generate .ocr.json file for an image using Azure Layout API.

    Args:
        client: DocumentIntelligenceClient instance
        image_path: Path to the image file
        output_path: Path for output JSON (defaults to image_path + .ocr.json)
        verbose: Print debug information

    Returns:
        The OCR JSON data
    """
    image_path = Path(image_path)
    output_path = Path(output_path) if output_path else image_path.parent / f"{image_path.name}.ocr.json"

    # Read image
    with open(image_path, "rb") as f:
        image_data = f.read()

    if verbose:
        print(f"Image size: {len(image_data)} bytes")
        print(f"Client endpoint: {client._config.endpoint}")

    # Capture raw response
    response_holder = {}

    # Call Layout API
    try:
        if verbose:
            print("Calling begin_analyze_document with model: prebuilt-layout")

        poller = client.begin_analyze_document(
            model_id="prebuilt-layout",
            body=image_data,
            content_type="application/octet-stream",
            cls=_capture_raw_response(response_holder),
        )
    except Exception as e:
        print(f"\n=== ERROR DETAILS ===")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")

        if hasattr(e, 'response'):
            print(f"\nHTTP Response:")
            resp = e.response
            print(f"  Status: {resp.status_code if hasattr(resp, 'status_code') else 'N/A'}")
            print(f"  Reason: {resp.reason if hasattr(resp, 'reason') else 'N/A'}")

            if hasattr(resp, 'text'):
                try:
                    body_text = resp.text() if callable(resp.text) else resp.text
                    print(f"  Body: {body_text}")
                except:
                    pass

            if hasattr(resp, 'headers'):
                print(f"  Headers: {dict(resp.headers)}")

        if hasattr(e, 'error'):
            print(f"\nError object: {e.error}")

        print("=" * 50)
        raise

    # Wait for completion
    result = poller.result()

    # Save raw response as .ocr.json
    if "raw" in response_holder:
        ocr_data = json.loads(response_holder["raw"])
        save_json(ocr_data, output_path)
        return ocr_data
    else:
        # Fallback: serialize the result object
        ocr_data = _serialize_analyze_result(result)
        save_json(ocr_data, output_path)
        return ocr_data


def _serialize_analyze_result(result: AnalyzeResult) -> dict[str, Any]:
    """Serialize AnalyzeResult to a dictionary matching API response format."""
    data = {
        "status": "succeeded",
        "analyzeResult": {
            "apiVersion": result.api_version,
            "modelId": result.model_id,
            "content": result.content,
            "pages": [],
        }
    }

    # Serialize pages
    for page in result.pages:
        page_data = {
            "pageNumber": page.page_number,
            "width": page.width,
            "height": page.height,
            "unit": page.unit,
            "words": [],
            "lines": [],
        }

        # Serialize words
        if page.words:
            for word in page.words:
                word_data = {
                    "content": word.content,
                    "confidence": word.confidence,
                }
                if word.polygon:
                    word_data["polygon"] = word.polygon
                if hasattr(word, "span") and word.span:
                    word_data["span"] = {
                        "offset": word.span.offset,
                        "length": word.span.length,
                    }
                page_data["words"].append(word_data)

        # Serialize lines
        if page.lines:
            for line in page.lines:
                line_data = {
                    "content": line.content,
                }
                if line.polygon:
                    line_data["polygon"] = line.polygon
                if hasattr(line, "spans") and line.spans:
                    line_data["spans"] = [
                        {"offset": s.offset, "length": s.length} for s in line.spans
                    ]
                page_data["lines"].append(line_data)

        data["analyzeResult"]["pages"].append(page_data)

    return data


def generate_ocr_json_batch(
    client: DocumentIntelligenceClient,
    image_paths: list[Path | str],
    output_dir: Optional[Path | str] = None,
    verbose: bool = True,
) -> list[dict]:
    """
    Generate .ocr.json files for multiple images.

    Args:
        client: DocumentIntelligenceClient instance
        image_paths: List of image paths
        output_dir: Directory for output files (defaults to same as each image)
        verbose: Print progress

    Returns:
        List of results with status for each image
    """
    results = []

    for i, image_path in enumerate(image_paths):
        image_path = Path(image_path)

        if verbose:
            print_progress(i + 1, len(image_paths), "Processing OCR")

        if output_dir:
            output_path = Path(output_dir) / f"{image_path.name}.ocr.json"
        else:
            output_path = None

        try:
            ocr_data = generate_ocr_json(client, image_path, output_path)
            results.append({
                "image": image_path.name,
                "success": True,
                "output": str(output_path or image_path.parent / f"{image_path.name}.ocr.json"),
                "pages": len(ocr_data.get("analyzeResult", {}).get("pages", [])),
            })
        except Exception as e:
            results.append({
                "image": image_path.name,
                "success": False,
                "error": str(e),
            })

    return results


def extract_words_from_ocr(ocr_data: dict[str, Any]) -> list[dict]:
    """
    Extract word data from OCR JSON.

    Args:
        ocr_data: OCR JSON data

    Returns:
        List of word dicts with text, polygon, confidence, page
    """
    words = []

    analyze_result = ocr_data.get("analyzeResult", ocr_data)
    pages = analyze_result.get("pages", [])

    for page in pages:
        page_num = page.get("pageNumber", 1)
        page_width = page.get("width", 1)
        page_height = page.get("height", 1)

        for word in page.get("words", []):
            word_data = {
                "text": word.get("content", ""),
                "confidence": word.get("confidence", 0.0),
                "page": page_num,
                "page_width": page_width,
                "page_height": page_height,
            }

            # Handle polygon coordinates
            polygon = word.get("polygon", [])
            if polygon:
                # Polygon is a flat list [x1,y1,x2,y2,...]
                word_data["polygon"] = polygon

                # Calculate bounding box
                if len(polygon) >= 8:
                    xs = polygon[0::2]
                    ys = polygon[1::2]
                    word_data["bbox"] = {
                        "x": min(xs),
                        "y": min(ys),
                        "width": max(xs) - min(xs),
                        "height": max(ys) - min(ys),
                    }

            # Include span data for reading order
            span = word.get("span", {})
            if span:
                word_data["span"] = span

            words.append(word_data)

    return words


def extract_selection_marks_from_ocr(ocr_data: dict[str, Any]) -> list[dict]:
    """
    Extract selection mark (checkbox) data from OCR JSON.

    Args:
        ocr_data: OCR JSON data

    Returns:
        List of selection mark dicts with state, polygon, confidence, page
    """
    selection_marks = []

    analyze_result = ocr_data.get("analyzeResult", ocr_data)
    pages = analyze_result.get("pages", [])

    for page in pages:
        page_num = page.get("pageNumber", 1)
        page_width = page.get("width", 1)
        page_height = page.get("height", 1)

        for mark in page.get("selectionMarks", []):
            mark_data = {
                "state": mark.get("state", "unselected"),
                "confidence": mark.get("confidence", 0.0),
                "page": page_num,
                "page_width": page_width,
                "page_height": page_height,
            }

            # Handle polygon coordinates
            polygon = mark.get("polygon", [])
            if polygon:
                # Polygon is a flat list [x1,y1,x2,y2,...]
                mark_data["polygon"] = polygon

                # Calculate bounding box
                if len(polygon) >= 8:
                    xs = polygon[0::2]
                    ys = polygon[1::2]
                    mark_data["bbox"] = {
                        "x": min(xs),
                        "y": min(ys),
                        "width": max(xs) - min(xs),
                        "height": max(ys) - min(ys),
                    }

            # Include span data for reading order
            span = mark.get("span", {})
            if span:
                mark_data["span"] = span

            selection_marks.append(mark_data)

    return selection_marks


def get_page_dimensions(ocr_data: dict[str, Any], page_num: int = 1) -> tuple[float, float]:
    """
    Get page dimensions from OCR data.

    Args:
        ocr_data: OCR JSON data
        page_num: Page number (1-indexed)

    Returns:
        Tuple of (width, height)
    """
    analyze_result = ocr_data.get("analyzeResult", ocr_data)
    pages = analyze_result.get("pages", [])

    for page in pages:
        if page.get("pageNumber", 1) == page_num:
            return page.get("width", 1), page.get("height", 1)

    # Default
    return 1, 1
