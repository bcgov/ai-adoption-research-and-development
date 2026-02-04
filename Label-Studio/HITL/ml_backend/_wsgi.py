# HITL/ml_backend/_wsgi.py
"""WSGI entry point for Label Studio ML backend."""

import os
import argparse
import logging

from label_studio_ml.api import init_app
from model import TesseractOCRModel

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.environ.get('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize the model
_model = TesseractOCRModel()

# Create the Flask app
app = init_app(model_class=TesseractOCRModel)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Label Studio ML Backend')
    parser.add_argument('--port', type=int, default=9090, help='Server port')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Server host')
    parser.add_argument('--debug', action='store_true', help='Debug mode')
    args = parser.parse_args()

    logger.info(f'Starting Tesseract OCR ML Backend on {args.host}:{args.port}')
    app.run(host=args.host, port=args.port, debug=args.debug)
