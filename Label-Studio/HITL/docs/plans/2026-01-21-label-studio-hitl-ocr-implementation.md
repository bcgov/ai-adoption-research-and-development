# Label Studio HITL OCR Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a local proof-of-concept for human-in-the-loop annotation of low-confidence OCR results using Label Studio with Tesseract.

**Architecture:** Docker Compose orchestrates 4 services (Label Studio, PostgreSQL, Tesseract ML Backend, Webhook Receiver). Images submitted via API get OCR pre-annotations; annotators correct low-confidence results; webhooks capture completed annotations.

**Tech Stack:** Docker, Label Studio, PostgreSQL, Python 3.11, FastAPI, pytesseract, label-studio-ml, label-studio-sdk

---

## Task 1: Environment Configuration

**Files:**
- Create: `HITL/.env`
- Create: `HITL/.env.example`

**Step 1: Create .env file with all configuration**

```bash
# HITL/.env

# Label Studio
LABEL_STUDIO_HOST=labelstudio
LABEL_STUDIO_PORT=8080
LABEL_STUDIO_USERNAME=admin@example.com
LABEL_STUDIO_PASSWORD=changeme123
LABEL_STUDIO_API_KEY=

# PostgreSQL
POSTGRES_USER=labelstudio
POSTGRES_PASSWORD=labelstudio_password
POSTGRES_DB=labelstudio
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# ML Backend
ML_BACKEND_HOST=ml_backend
ML_BACKEND_PORT=9090
CONFIDENCE_THRESHOLD=0.75

# Webhook Receiver
WEBHOOK_HOST=webhook_receiver
WEBHOOK_PORT=8000

# Network
DOCKER_NETWORK=hitl-network
```

**Step 2: Create .env.example (same content, safe to commit)**

Copy `.env` to `.env.example` and keep passwords as placeholders.

**Step 3: Commit**

```bash
git add HITL/.env.example
git commit -m "feat: add environment configuration template for HITL"
```

> Note: `.env` should be in `.gitignore`

---

## Task 2: Docker Compose Setup

**Files:**
- Create: `HITL/docker-compose.yml`

**Step 1: Create docker-compose.yml with all 4 services**

```yaml
# HITL/docker-compose.yml

services:
  postgres:
    image: postgres:16-alpine
    container_name: hitl-postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - hitl-network

  labelstudio:
    image: heartexlabs/label-studio:latest
    container_name: hitl-labelstudio
    ports:
      - "${LABEL_STUDIO_PORT}:8080"
    environment:
      DJANGO_DB: default
      POSTGRE_NAME: ${POSTGRES_DB}
      POSTGRE_USER: ${POSTGRES_USER}
      POSTGRE_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRE_HOST: ${POSTGRES_HOST}
      POSTGRE_PORT: ${POSTGRES_PORT}
      LABEL_STUDIO_USERNAME: ${LABEL_STUDIO_USERNAME}
      LABEL_STUDIO_PASSWORD: ${LABEL_STUDIO_PASSWORD}
      LABEL_STUDIO_LOCAL_FILES_SERVING_ENABLED: "true"
      LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT: /label-studio/data/images
    volumes:
      - labelstudio_data:/label-studio/data
      - ./images:/label-studio/data/images:ro
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 10s
      timeout: 10s
      retries: 10
      start_period: 30s
    networks:
      - hitl-network

  ml_backend:
    build:
      context: ./ml_backend
      dockerfile: Dockerfile
    container_name: hitl-ml-backend
    ports:
      - "${ML_BACKEND_PORT}:9090"
    environment:
      LABEL_STUDIO_URL: http://${LABEL_STUDIO_HOST}:8080
      CONFIDENCE_THRESHOLD: ${CONFIDENCE_THRESHOLD}
    volumes:
      - ./images:/app/images:ro
    depends_on:
      labelstudio:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9090/health"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - hitl-network

  webhook_receiver:
    build:
      context: ./webhook_receiver
      dockerfile: Dockerfile
    container_name: hitl-webhook
    ports:
      - "${WEBHOOK_PORT}:8000"
    volumes:
      - webhook_data:/app/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - hitl-network

volumes:
  postgres_data:
  labelstudio_data:
  webhook_data:

networks:
  hitl-network:
    driver: bridge
```

**Step 2: Verify syntax**

Run: `cd HITL && docker compose config`
Expected: YAML parsed successfully, no errors

**Step 3: Commit**

```bash
git add HITL/docker-compose.yml
git commit -m "feat: add Docker Compose orchestration for HITL services"
```

---

## Task 3: Labeling Configuration

**Files:**
- Create: `HITL/config/labeling_config.xml`

**Step 1: Create the labeling config XML**

```xml
<!-- HITL/config/labeling_config.xml -->
<View>
  <Image name="image" value="$image" zoom="true" zoomControl="true"
         rotateControl="true" width="100%" height="100%"
         maxHeight="auto" maxWidth="auto"/>

  <RectangleLabels name="bbox" toName="image" strokeWidth="2" smart="true">
    <Label value="Text" background="green"/>
  </RectangleLabels>

  <TextArea name="transcription" toName="image"
            editable="true" perRegion="true" required="true"
            maxSubmissions="1" rows="3" placeholder="Recognized Text"
            displayMode="region-list"/>

  <Choices name="status" toName="image" perRegion="true" required="true">
    <Choice value="Accepted"/>
    <Choice value="Rejected"/>
    <Choice value="Needs Review"/>
  </Choices>
</View>
```

**Step 2: Commit**

```bash
git add HITL/config/labeling_config.xml
git commit -m "feat: add Label Studio labeling config for OCR annotation"
```

---

## Task 4: Tesseract ML Backend - OCR Processor

**Files:**
- Create: `HITL/ml_backend/ocr_processor.py`
- Create: `HITL/ml_backend/requirements.txt`

**Step 1: Create requirements.txt**

```text
# HITL/ml_backend/requirements.txt
label-studio-ml==1.0.9
pytesseract==0.3.10
Pillow==10.2.0
requests==2.31.0
gunicorn==21.2.0
```

**Step 2: Create ocr_processor.py**

```python
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
```

**Step 3: Commit**

```bash
git add HITL/ml_backend/requirements.txt HITL/ml_backend/ocr_processor.py
git commit -m "feat: add Tesseract OCR processor with confidence scoring"
```

---

## Task 5: Tesseract ML Backend - Model

**Files:**
- Create: `HITL/ml_backend/model.py`

**Step 1: Create model.py implementing Label Studio ML backend protocol**

```python
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
```

**Step 2: Commit**

```bash
git add HITL/ml_backend/model.py
git commit -m "feat: add Label Studio ML backend model for Tesseract OCR"
```

---

## Task 6: Tesseract ML Backend - Dockerfile

**Files:**
- Create: `HITL/ml_backend/Dockerfile`

**Step 1: Create Dockerfile**

```dockerfile
# HITL/ml_backend/Dockerfile
FROM python:3.11-slim

# Install Tesseract OCR
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1-mesa-glx \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ocr_processor.py .
COPY model.py .

# Expose port
EXPOSE 9090

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD curl -f http://localhost:9090/health || exit 1

# Start the ML backend server
CMD ["label-studio-ml", "start", "./", "--host", "0.0.0.0", "--port", "9090"]
```

**Step 2: Commit**

```bash
git add HITL/ml_backend/Dockerfile
git commit -m "feat: add Dockerfile for Tesseract ML backend"
```

---

## Task 7: Webhook Receiver - FastAPI App

**Files:**
- Create: `HITL/webhook_receiver/main.py`
- Create: `HITL/webhook_receiver/requirements.txt`

**Step 1: Create requirements.txt**

```text
# HITL/webhook_receiver/requirements.txt
fastapi==0.109.0
uvicorn==0.27.0
pydantic==2.5.3
```

**Step 2: Create main.py**

```python
# HITL/webhook_receiver/main.py
"""FastAPI webhook receiver for Label Studio annotations."""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


app = FastAPI(title="HITL Webhook Receiver")

# Storage path
DATA_DIR = "/app/data"
ANNOTATIONS_FILE = os.path.join(DATA_DIR, "annotations.json")


class AnnotationRegion(BaseModel):
    """Extracted region from annotation."""
    bbox: List[float]
    text: str
    status: str


class StoredAnnotation(BaseModel):
    """Stored annotation format."""
    task_id: int
    image_path: str
    regions: List[AnnotationRegion]
    completed_at: str
    raw_result: Optional[Dict[str, Any]] = None


def load_annotations() -> List[Dict]:
    """Load annotations from JSON file."""
    if not os.path.exists(ANNOTATIONS_FILE):
        return []
    with open(ANNOTATIONS_FILE, 'r') as f:
        return json.load(f)


def save_annotations(annotations: List[Dict]):
    """Save annotations to JSON file."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(ANNOTATIONS_FILE, 'w') as f:
        json.dump(annotations, f, indent=2)


def extract_regions(result: List[Dict]) -> List[AnnotationRegion]:
    """
    Extract regions from Label Studio annotation result.

    Groups rectanglelabels, textarea, and choices by region ID.
    """
    # Group by region ID
    regions_by_id = {}

    for item in result:
        region_id = item.get('id')
        if not region_id:
            continue

        if region_id not in regions_by_id:
            regions_by_id[region_id] = {
                'bbox': None,
                'text': '',
                'status': 'Unknown'
            }

        item_type = item.get('type')
        value = item.get('value', {})

        if item_type == 'rectanglelabels':
            regions_by_id[region_id]['bbox'] = [
                value.get('x', 0),
                value.get('y', 0),
                value.get('width', 0),
                value.get('height', 0)
            ]
        elif item_type == 'textarea':
            text_list = value.get('text', [])
            regions_by_id[region_id]['text'] = text_list[0] if text_list else ''
        elif item_type == 'choices':
            choices = value.get('choices', [])
            regions_by_id[region_id]['status'] = choices[0] if choices else 'Unknown'

    # Convert to list, filtering out incomplete regions
    regions = []
    for region_data in regions_by_id.values():
        if region_data['bbox'] is not None:
            regions.append(AnnotationRegion(**region_data))

    return regions


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/webhook/annotation")
async def receive_annotation(payload: Dict[str, Any]):
    """
    Receive webhook from Label Studio when annotation is created/updated.

    Expected payload:
    {
        "action": "ANNOTATION_CREATED" | "ANNOTATION_UPDATED",
        "annotation": {
            "id": int,
            "result": [...],
            "task": int
        },
        "task": {
            "id": int,
            "data": {"image": "..."}
        }
    }
    """
    action = payload.get('action')

    if action not in ('ANNOTATION_CREATED', 'ANNOTATION_UPDATED'):
        return {"status": "ignored", "reason": f"action {action} not handled"}

    annotation = payload.get('annotation', {})
    task = payload.get('task', {})

    task_id = task.get('id')
    image_path = task.get('data', {}).get('image', '')
    result = annotation.get('result', [])

    if not task_id:
        raise HTTPException(status_code=400, detail="Missing task ID")

    # Extract regions from annotation
    regions = extract_regions(result)

    # Create stored annotation
    stored = StoredAnnotation(
        task_id=task_id,
        image_path=image_path,
        regions=regions,
        completed_at=datetime.utcnow().isoformat(),
        raw_result=result
    )

    # Load existing, append, save
    annotations = load_annotations()

    # Update if exists, otherwise append
    existing_idx = next(
        (i for i, a in enumerate(annotations) if a['task_id'] == task_id),
        None
    )
    if existing_idx is not None:
        annotations[existing_idx] = stored.model_dump()
    else:
        annotations.append(stored.model_dump())

    save_annotations(annotations)

    return {
        "status": "received",
        "task_id": task_id,
        "regions_count": len(regions)
    }


@app.get("/annotations")
async def get_annotations(
    task_id: Optional[int] = None,
    status: Optional[str] = None
):
    """
    Query stored annotations.

    Args:
        task_id: Filter by specific task ID
        status: Filter by region status (Accepted, Rejected, Needs Review)
    """
    annotations = load_annotations()

    if task_id is not None:
        annotations = [a for a in annotations if a['task_id'] == task_id]

    if status is not None:
        # Filter annotations that have at least one region with this status
        filtered = []
        for a in annotations:
            matching_regions = [r for r in a['regions'] if r['status'] == status]
            if matching_regions:
                filtered.append({
                    **a,
                    'regions': matching_regions
                })
        annotations = filtered

    return {
        "count": len(annotations),
        "annotations": annotations
    }


@app.get("/annotations/{task_id}")
async def get_annotation_by_task(task_id: int):
    """Get annotation for a specific task."""
    annotations = load_annotations()

    for a in annotations:
        if a['task_id'] == task_id:
            return a

    raise HTTPException(status_code=404, detail=f"No annotation for task {task_id}")
```

**Step 3: Commit**

```bash
git add HITL/webhook_receiver/requirements.txt HITL/webhook_receiver/main.py
git commit -m "feat: add FastAPI webhook receiver for annotations"
```

---

## Task 8: Webhook Receiver - Dockerfile

**Files:**
- Create: `HITL/webhook_receiver/Dockerfile`

**Step 1: Create Dockerfile**

```dockerfile
# HITL/webhook_receiver/Dockerfile
FROM python:3.11-slim

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .

# Create data directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start the server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 2: Commit**

```bash
git add HITL/webhook_receiver/Dockerfile
git commit -m "feat: add Dockerfile for webhook receiver"
```

---

## Task 9: Python Client - Label Studio SDK Wrapper

**Files:**
- Create: `HITL/client/label_studio_client.py`
- Create: `HITL/client/requirements.txt`

**Step 1: Create requirements.txt**

```text
# HITL/client/requirements.txt
label-studio-sdk==0.0.34
python-dotenv==1.0.0
requests==2.31.0
```

**Step 2: Create label_studio_client.py**

```python
# HITL/client/label_studio_client.py
"""Label Studio SDK client wrapper for HITL OCR workflow."""

import os
from typing import List, Optional

from dotenv import load_dotenv
from label_studio_sdk import Client


class HITLClient:
    """Client for interacting with Label Studio for HITL OCR workflow."""

    def __init__(self, url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize the client.

        Args:
            url: Label Studio URL (default: from env LABEL_STUDIO_URL)
            api_key: API key (default: from env LABEL_STUDIO_API_KEY)
        """
        load_dotenv()

        self.url = url or os.environ.get(
            'LABEL_STUDIO_URL',
            f"http://localhost:{os.environ.get('LABEL_STUDIO_PORT', '8080')}"
        )
        self.api_key = api_key or os.environ.get('LABEL_STUDIO_API_KEY')

        if not self.api_key:
            raise ValueError(
                "API key required. Set LABEL_STUDIO_API_KEY env var or pass api_key parameter. "
                "Get your API key from Label Studio > Account & Settings > Access Token"
            )

        self.client = Client(url=self.url, api_key=self.api_key)

    def create_project(
        self,
        name: str,
        labeling_config_path: str,
        description: str = ""
    ) -> int:
        """
        Create a new Label Studio project.

        Args:
            name: Project name
            labeling_config_path: Path to labeling_config.xml
            description: Optional project description

        Returns:
            Project ID
        """
        with open(labeling_config_path, 'r') as f:
            labeling_config = f.read()

        project = self.client.start_project(
            title=name,
            label_config=labeling_config,
            description=description
        )

        return project.id

    def configure_ml_backend(
        self,
        project_id: int,
        ml_backend_url: str,
        title: str = "Tesseract OCR"
    ) -> int:
        """
        Connect an ML backend to a project.

        Args:
            project_id: Project ID
            ml_backend_url: URL of the ML backend
            title: Display name for the ML backend

        Returns:
            ML backend ID
        """
        project = self.client.get_project(project_id)

        ml_backend = project.connect_ml_backend(
            url=ml_backend_url,
            title=title
        )

        return ml_backend.id

    def configure_webhook(
        self,
        project_id: int,
        webhook_url: str,
        actions: Optional[List[str]] = None
    ) -> int:
        """
        Set up a webhook for annotation events.

        Args:
            project_id: Project ID
            webhook_url: URL to receive webhooks
            actions: List of actions to trigger webhook (default: ANNOTATION_CREATED, ANNOTATION_UPDATED)

        Returns:
            Webhook ID
        """
        if actions is None:
            actions = ['ANNOTATION_CREATED', 'ANNOTATION_UPDATED']

        project = self.client.get_project(project_id)

        # Use the webhooks API directly
        import requests
        response = requests.post(
            f"{self.url}/api/webhooks",
            headers={"Authorization": f"Token {self.api_key}"},
            json={
                "url": webhook_url,
                "project": project_id,
                "send_payload": True,
                "send_for_all_actions": False,
                "actions": actions
            }
        )
        response.raise_for_status()

        return response.json()['id']

    def create_task(
        self,
        project_id: int,
        image_path: str
    ) -> int:
        """
        Create a task with an image.

        Args:
            project_id: Project ID
            image_path: Path or URL to the image

        Returns:
            Task ID
        """
        project = self.client.get_project(project_id)

        task = project.import_tasks([
            {"image": image_path}
        ])

        return task[0]['id']

    def create_tasks_from_directory(
        self,
        project_id: int,
        directory: str,
        extensions: Optional[List[str]] = None
    ) -> List[int]:
        """
        Create tasks for all images in a directory.

        Args:
            project_id: Project ID
            directory: Path to directory containing images
            extensions: File extensions to include (default: jpg, jpeg, png)

        Returns:
            List of task IDs
        """
        if extensions is None:
            extensions = ['.jpg', '.jpeg', '.png']

        project = self.client.get_project(project_id)

        # Find all image files
        tasks_data = []
        for filename in os.listdir(directory):
            ext = os.path.splitext(filename)[1].lower()
            if ext in extensions:
                # Use local file serving path
                tasks_data.append({
                    "image": f"/data/local-files/?d=images/{filename}"
                })

        if not tasks_data:
            return []

        tasks = project.import_tasks(tasks_data)
        return [t['id'] for t in tasks]

    def get_annotations(
        self,
        project_id: int,
        only_completed: bool = True
    ) -> List[dict]:
        """
        Get annotations for a project.

        Args:
            project_id: Project ID
            only_completed: Only return completed annotations

        Returns:
            List of annotations
        """
        project = self.client.get_project(project_id)

        tasks = project.get_labeled_tasks() if only_completed else project.get_tasks()

        annotations = []
        for task in tasks:
            for annotation in task.get('annotations', []):
                annotations.append({
                    'task_id': task['id'],
                    'annotation_id': annotation['id'],
                    'result': annotation['result'],
                    'created_at': annotation.get('created_at')
                })

        return annotations

    def trigger_predictions(self, project_id: int, ml_backend_id: int):
        """
        Trigger ML backend predictions for all tasks in a project.

        Args:
            project_id: Project ID
            ml_backend_id: ML backend ID
        """
        import requests
        response = requests.post(
            f"{self.url}/api/ml/{ml_backend_id}/predict",
            headers={"Authorization": f"Token {self.api_key}"}
        )
        response.raise_for_status()
```

**Step 3: Commit**

```bash
git add HITL/client/requirements.txt HITL/client/label_studio_client.py
git commit -m "feat: add Label Studio SDK client wrapper"
```

---

## Task 10: Setup Script

**Files:**
- Create: `HITL/scripts/setup_project.py`

**Step 1: Create setup_project.py**

```python
#!/usr/bin/env python3
# HITL/scripts/setup_project.py
"""One-time setup script for HITL OCR project."""

import os
import sys
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.label_studio_client import HITLClient


def wait_for_label_studio(url: str, max_retries: int = 30, delay: int = 2):
    """Wait for Label Studio to be ready."""
    import requests

    print(f"Waiting for Label Studio at {url}...")

    for i in range(max_retries):
        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                print("Label Studio is ready!")
                return True
        except requests.exceptions.RequestException:
            pass

        print(f"  Attempt {i+1}/{max_retries}...")
        time.sleep(delay)

    print("Label Studio not available")
    return False


def main():
    """Set up the HITL OCR project."""
    # Configuration
    project_name = "HITL OCR Review"
    project_description = "Human-in-the-loop review of low-confidence OCR results"

    label_studio_url = os.environ.get('LABEL_STUDIO_URL', 'http://localhost:8080')
    ml_backend_url = os.environ.get('ML_BACKEND_URL', 'http://ml_backend:9090')
    webhook_url = os.environ.get('WEBHOOK_URL', 'http://webhook_receiver:8000/webhook/annotation')

    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'config',
        'labeling_config.xml'
    )

    # Wait for Label Studio
    if not wait_for_label_studio(label_studio_url):
        print("ERROR: Label Studio is not available. Make sure docker-compose is running.")
        sys.exit(1)

    # Initialize client
    try:
        client = HITLClient(url=label_studio_url)
    except ValueError as e:
        print(f"ERROR: {e}")
        print("\nTo get your API key:")
        print("1. Log in to Label Studio at http://localhost:8080")
        print("2. Go to Account & Settings > Access Token")
        print("3. Copy the token and set: export LABEL_STUDIO_API_KEY=<your-token>")
        sys.exit(1)

    print(f"\nCreating project: {project_name}")
    project_id = client.create_project(
        name=project_name,
        labeling_config_path=config_path,
        description=project_description
    )
    print(f"  Project ID: {project_id}")

    print(f"\nConnecting ML backend: {ml_backend_url}")
    try:
        ml_backend_id = client.configure_ml_backend(
            project_id=project_id,
            ml_backend_url=ml_backend_url
        )
        print(f"  ML Backend ID: {ml_backend_id}")
    except Exception as e:
        print(f"  WARNING: Could not connect ML backend: {e}")
        print("  You may need to connect it manually in Label Studio settings")
        ml_backend_id = None

    print(f"\nConfiguring webhook: {webhook_url}")
    try:
        webhook_id = client.configure_webhook(
            project_id=project_id,
            webhook_url=webhook_url
        )
        print(f"  Webhook ID: {webhook_id}")
    except Exception as e:
        print(f"  WARNING: Could not configure webhook: {e}")
        print("  You may need to configure it manually in Label Studio settings")

    print("\n" + "="*50)
    print("Setup complete!")
    print("="*50)
    print(f"\nProject URL: {label_studio_url}/projects/{project_id}")
    print("\nNext steps:")
    print("1. Run: python scripts/submit_sample_tasks.py")
    print("2. Open Label Studio and start annotating")


if __name__ == '__main__':
    main()
```

**Step 2: Make executable**

```bash
chmod +x HITL/scripts/setup_project.py
```

**Step 3: Commit**

```bash
git add HITL/scripts/setup_project.py
git commit -m "feat: add project setup script"
```

---

## Task 11: Sample Task Submission Script

**Files:**
- Create: `HITL/scripts/submit_sample_tasks.py`

**Step 1: Create submit_sample_tasks.py**

```python
#!/usr/bin/env python3
# HITL/scripts/submit_sample_tasks.py
"""Submit sample images as tasks to Label Studio."""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.label_studio_client import HITLClient


def main():
    """Submit sample images from the images directory."""
    label_studio_url = os.environ.get('LABEL_STUDIO_URL', 'http://localhost:8080')

    images_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'images'
    )

    # Get project ID from command line or find the first project
    project_id = None
    if len(sys.argv) > 1:
        project_id = int(sys.argv[1])

    # Initialize client
    try:
        client = HITLClient(url=label_studio_url)
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Find project if not specified
    if project_id is None:
        projects = client.client.get_projects()
        if not projects:
            print("ERROR: No projects found. Run setup_project.py first.")
            sys.exit(1)
        project_id = projects[0].id
        print(f"Using project: {projects[0].title} (ID: {project_id})")

    # Check for images
    if not os.path.exists(images_dir):
        print(f"ERROR: Images directory not found: {images_dir}")
        sys.exit(1)

    image_files = [
        f for f in os.listdir(images_dir)
        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
    ]

    if not image_files:
        print(f"No images found in {images_dir}")
        print("Add some .jpg or .png files to test the OCR workflow")
        sys.exit(0)

    print(f"\nFound {len(image_files)} images in {images_dir}")
    print("Submitting tasks...")

    task_ids = client.create_tasks_from_directory(
        project_id=project_id,
        directory=images_dir
    )

    print(f"\nCreated {len(task_ids)} tasks:")
    for i, (filename, task_id) in enumerate(zip(image_files, task_ids)):
        print(f"  {i+1}. {filename} -> Task ID: {task_id}")

    print(f"\nOpen Label Studio to start annotating:")
    print(f"  {label_studio_url}/projects/{project_id}/data")


if __name__ == '__main__':
    main()
```

**Step 2: Make executable**

```bash
chmod +x HITL/scripts/submit_sample_tasks.py
```

**Step 3: Commit**

```bash
git add HITL/scripts/submit_sample_tasks.py
git commit -m "feat: add sample task submission script"
```

---

## Task 12: Add .gitignore

**Files:**
- Create: `HITL/.gitignore`

**Step 1: Create .gitignore**

```gitignore
# HITL/.gitignore

# Environment
.env

# Python
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
*.egg-info/
dist/
build/

# Data
data/
*.json

# Docker volumes
postgres_data/
labelstudio_data/
webhook_data/

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
```

**Step 2: Commit**

```bash
git add HITL/.gitignore
git commit -m "chore: add .gitignore for HITL"
```

---

## Task 13: Integration Test

**Files:**
- None (manual verification)

**Step 1: Start all services**

```bash
cd HITL
docker compose up -d --build
```

Expected: All 4 containers start and become healthy

**Step 2: Check service health**

```bash
docker compose ps
```

Expected: All services show "healthy" status

**Step 3: Get API key from Label Studio**

1. Open http://localhost:8080
2. Log in with admin@example.com / changeme123
3. Go to Account & Settings > Access Token
4. Copy the token

```bash
export LABEL_STUDIO_API_KEY=<your-token>
```

**Step 4: Run setup script**

```bash
cd HITL
python scripts/setup_project.py
```

Expected: Project created, ML backend connected, webhook configured

**Step 5: Submit sample tasks**

```bash
python scripts/submit_sample_tasks.py
```

Expected: Tasks created from images in `images/` directory

**Step 6: Verify in Label Studio UI**

1. Open http://localhost:8080
2. Navigate to the project
3. Click on a task
4. Verify OCR bounding boxes and text appear
5. Make corrections, select Accept/Reject for each region
6. Submit the annotation

**Step 7: Verify webhook received annotation**

```bash
curl http://localhost:8000/annotations
```

Expected: JSON response with the submitted annotation

**Step 8: Commit final verification**

```bash
git add -A
git commit -m "feat: complete HITL OCR annotation system"
```

---

## Summary

| Task | Files | Description |
|------|-------|-------------|
| 1 | `.env`, `.env.example` | Environment configuration |
| 2 | `docker-compose.yml` | Service orchestration |
| 3 | `config/labeling_config.xml` | Label Studio UI template |
| 4 | `ml_backend/ocr_processor.py`, `requirements.txt` | Tesseract OCR processing |
| 5 | `ml_backend/model.py` | Label Studio ML backend |
| 6 | `ml_backend/Dockerfile` | ML backend container |
| 7 | `webhook_receiver/main.py`, `requirements.txt` | FastAPI webhook handler |
| 8 | `webhook_receiver/Dockerfile` | Webhook container |
| 9 | `client/label_studio_client.py`, `requirements.txt` | SDK wrapper |
| 10 | `scripts/setup_project.py` | One-time setup |
| 11 | `scripts/submit_sample_tasks.py` | Task submission demo |
| 12 | `.gitignore` | Git ignore rules |
| 13 | Manual | Integration testing |
