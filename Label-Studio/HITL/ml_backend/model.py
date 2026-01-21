# HITL/ml_backend/model.py
"""Label Studio ML Backend for Tesseract OCR."""

import os
import requests
from urllib.parse import urlparse
from label_studio_ml.model import LabelStudioMLBase
from ocr_processor import process_image, format_for_label_studio


class TesseractOCRModel(LabelStudioMLBase):
    """ML Backend that runs Tesseract OCR on images."""

    def __init__(self, **kwargs):
        super(TesseractOCRModel, self).__init__(**kwargs)
        self.confidence_threshold = float(os.environ.get('CONFIDENCE_THRESHOLD', 0.75))

    def predict(self, tasks, **kwargs):
        """
        Run OCR on each task's image and return predictions.

        Args:
            tasks: List of Label Studio tasks

        Returns:
            List of predictions in Label Studio format
        """
        predictions = []

        for task in tasks:
            image_url = task['data'].get('image')
            if not image_url:
                predictions.append({'result': [], 'score': 0})
                continue

            # Download image if it's a URL
            image_path = self._get_image_path(image_url)
            if not image_path:
                predictions.append({'result': [], 'score': 0})
                continue

            try:
                # Run OCR
                ocr_result = process_image(image_path)

                # Format for Label Studio
                prediction = format_for_label_studio(ocr_result)
                predictions.append(prediction)

            except Exception as e:
                print(f"Error processing image: {e}")
                predictions.append({'result': [], 'score': 0})
            finally:
                # Clean up downloaded file if needed
                if image_path.startswith('/tmp/'):
                    os.remove(image_path)

        return predictions

    def _get_image_path(self, image_url: str) -> str:
        """
        Get local path for an image URL.

        Handles:
        - Local file paths
        - HTTP/HTTPS URLs (downloads to temp)
        - Label Studio local file serving URLs
        """
        parsed = urlparse(image_url)

        # Local file path
        if not parsed.scheme or parsed.scheme == 'file':
            local_path = parsed.path
            if os.path.exists(local_path):
                return local_path
            # Try relative to images directory
            images_path = f"/app/images/{os.path.basename(local_path)}"
            if os.path.exists(images_path):
                return images_path
            return None

        # HTTP URL - download
        if parsed.scheme in ('http', 'https'):
            try:
                response = requests.get(image_url, timeout=30)
                response.raise_for_status()

                # Save to temp file
                ext = os.path.splitext(parsed.path)[1] or '.jpg'
                temp_path = f"/tmp/ls_image_{hash(image_url)}{ext}"
                with open(temp_path, 'wb') as f:
                    f.write(response.content)
                return temp_path
            except Exception as e:
                print(f"Error downloading image: {e}")
                return None

        return None

    def fit(self, annotations, **kwargs):
        """
        Training method - not implemented for this POC.
        """
        return {}
