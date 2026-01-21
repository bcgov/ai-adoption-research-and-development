# HITL/ml_backend/ocr_processor.py
"""Tesseract OCR processor with confidence scoring."""

import pytesseract
from PIL import Image
from typing import List, Dict, Any
import uuid


def process_image(image_path: str) -> Dict[str, Any]:
    """
    Run OCR on an image and return regions with confidence scores.

    Args:
        image_path: Path to the image file

    Returns:
        Dict with 'regions' list and 'overall_score'
    """
    image = Image.open(image_path)
    width, height = image.size

    # Get detailed OCR data with confidence
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

    regions = []
    confidences = []

    # Group by block_num to get text blocks
    current_block = None
    block_text = []
    block_conf = []
    block_bbox = None

    for i in range(len(data['text'])):
        text = data['text'][i].strip()
        conf = data['conf'][i]
        block_num = data['block_num'][i]

        # Skip empty entries or low confidence (-1 means no confidence)
        if not text or conf == -1:
            continue

        # New block detected
        if block_num != current_block:
            # Save previous block if exists
            if current_block is not None and block_text:
                regions.append({
                    'text': ' '.join(block_text),
                    'bbox': block_bbox,
                    'confidence': sum(block_conf) / len(block_conf) / 100  # Normalize to 0-1
                })
                confidences.append(sum(block_conf) / len(block_conf) / 100)

            # Start new block
            current_block = block_num
            block_text = [text]
            block_conf = [conf]
            block_bbox = {
                'x': data['left'][i] / width * 100,
                'y': data['top'][i] / height * 100,
                'width': data['width'][i] / width * 100,
                'height': data['height'][i] / height * 100
            }
        else:
            # Extend current block
            block_text.append(text)
            block_conf.append(conf)
            # Expand bbox to include this word
            new_right = (data['left'][i] + data['width'][i]) / width * 100
            new_bottom = (data['top'][i] + data['height'][i]) / height * 100
            current_right = block_bbox['x'] + block_bbox['width']
            current_bottom = block_bbox['y'] + block_bbox['height']
            block_bbox['width'] = max(new_right, current_right) - block_bbox['x']
            block_bbox['height'] = max(new_bottom, current_bottom) - block_bbox['y']

    # Don't forget the last block
    if block_text:
        regions.append({
            'text': ' '.join(block_text),
            'bbox': block_bbox,
            'confidence': sum(block_conf) / len(block_conf) / 100
        })
        confidences.append(sum(block_conf) / len(block_conf) / 100)

    overall_score = min(confidences) if confidences else 0.0

    return {
        'regions': regions,
        'overall_score': overall_score,
        'image_width': width,
        'image_height': height
    }


def format_for_label_studio(ocr_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert OCR result to Label Studio prediction format.

    Args:
        ocr_result: Output from process_image()

    Returns:
        Label Studio prediction dict
    """
    result = []

    for region in ocr_result['regions']:
        region_id = str(uuid.uuid4())[:8]

        # Rectangle label for bounding box
        result.append({
            'id': region_id,
            'type': 'rectanglelabels',
            'from_name': 'bbox',
            'to_name': 'image',
            'original_width': ocr_result['image_width'],
            'original_height': ocr_result['image_height'],
            'image_rotation': 0,
            'value': {
                'x': region['bbox']['x'],
                'y': region['bbox']['y'],
                'width': region['bbox']['width'],
                'height': region['bbox']['height'],
                'rotation': 0,
                'rectanglelabels': ['Text']
            }
        })

        # TextArea for transcription (linked by same ID)
        result.append({
            'id': region_id,
            'type': 'textarea',
            'from_name': 'transcription',
            'to_name': 'image',
            'value': {
                'text': [region['text']]
            }
        })

    return {
        'result': result,
        'score': ocr_result['overall_score']
    }
