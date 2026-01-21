# Label Studio HITL OCR Annotation System

## Overview

Set up Label Studio for human-in-the-loop annotation of low-confidence OCR results.

**Scope:** Local proof-of-concept with Tesseract OCR, automated confidence flagging, and webhook-based annotation capture.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Docker Compose Network                      │
├─────────────────┬─────────────────┬─────────────────┬───────────┤
│  Label Studio   │   PostgreSQL    │  Tesseract ML   │  Webhook  │
│   (UI + API)    │   (Storage)     │    Backend      │  Receiver │
│   Port 8080     │   Port 5432     │   Port 9090     │  Port 8000│
└────────┬────────┴────────┬────────┴────────┬────────┴─────┬─────┘
         │                 │                 │              │
         │ stores tasks    │ pre-annotates   │   receives   │
         │ & annotations   │ with OCR        │   webhooks   │
         └─────────────────┴─────────────────┴──────────────┘
```

**Workflow:**
1. Submit image via API → Label Studio creates task
2. Tesseract ML backend runs OCR, returns text + bounding boxes + confidence score
3. Low-confidence tasks (score < 0.75) surfaced via Data Manager filtering/sorting
4. Annotator corrects text/boxes, accepts or rejects each region
5. On submit → webhook fires to receiver → stores/processes result

---

## File Structure

```
HITL/
├── docker-compose.yml          # All 4 services orchestrated
├── .env                        # Configuration (ports, credentials, thresholds)
├── images/                     # Sample test images (already exists)
│
├── ml_backend/                 # Tesseract ML Backend
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── model.py                # Label Studio ML backend interface
│   └── ocr_processor.py        # Tesseract wrapper with confidence scoring
│
├── webhook_receiver/           # FastAPI webhook handler
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py                 # Receives annotation webhooks
│
├── client/                     # Python SDK for programmatic access
│   ├── requirements.txt
│   └── label_studio_client.py  # Create projects, submit tasks, query results
│
├── config/
│   └── labeling_config.xml     # Label Studio UI template (image + OCR + text)
│
└── scripts/
    ├── setup_project.py        # One-time setup: create project, configure ML
    └── submit_sample_tasks.py  # Demo: submit test images
```

---

## Component Details

### 1. Tesseract ML Backend

**Purpose:** Automatically run OCR on uploaded images and return pre-annotations with confidence scores.

**Files:**
- `model.py` - Label Studio ML backend protocol implementation
  - `predict()` - Called on task creation; runs OCR, returns pre-annotations
  - `fit()` - Skipped for POC
- `ocr_processor.py` - Tesseract wrapper
  - Uses `pytesseract` with `image_to_data()` for word-level confidence
  - Groups words into text regions (lines or blocks)
  - Returns confidence score normalized to 0-1

**Confidence scoring:**
- Tesseract returns word-level confidence (0-100, normalized to 0-1)
- Overall task score = minimum confidence across all detected regions
- Tasks with score < 0.75 are prioritized for review via Data Manager filtering
- Annotators sort by score (ascending) to work on low-confidence items first

**ML Backend prediction format (Label Studio protocol):**
```python
{
    "result": [
        {
            "id": "region-1",
            "type": "rectanglelabels",
            "from_name": "bbox",
            "to_name": "image",
            "original_width": 1000,   # actual image width in pixels
            "original_height": 800,   # actual image height in pixels
            "image_rotation": 0,
            "value": {
                "x": 10.5,            # percentage from left
                "y": 20.3,            # percentage from top
                "width": 30.0,        # percentage of image width
                "height": 5.0,        # percentage of image height
                "rotation": 0,
                "rectanglelabels": ["Text"]
            }
        },
        {
            "id": "region-1",         # same ID links textarea to bbox
            "type": "textarea",
            "from_name": "transcription",
            "to_name": "image",
            "value": {
                "text": ["extracted text here"]
            }
        }
    ],
    "score": 0.82                     # overall confidence (min across regions)
}
```

### 2. Labeling Configuration

**XML Template (`config/labeling_config.xml`):**
```xml
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

**Key attributes:**
- `smart="true"` on RectangleLabels enables ML backend integration
- `perRegion="true"` on TextArea and Choices binds them to individual bounding boxes
- `$image` is the task data field (standardized variable name)

**Annotator workflow:**
1. Image loads with pre-annotated bounding boxes from ML backend
2. Each box has associated text field and accept/reject choices
3. Annotator can: adjust box position/size, edit text, mark status
4. Submit saves all corrections

### 3. Webhook Receiver

**FastAPI endpoints:**
- `POST /webhook/annotation` - Receives Label Studio webhook on submit
- `GET /annotations` - Query stored annotations
- `GET /health` - Health check

**Payload processing:**
```python
# Input from Label Studio:
{
    "action": "ANNOTATION_CREATED",
    "annotation": {
        "result": [...],  # boxes, text, choices
        "task": { "data": { "image": "..." } }
    }
}

# Stored format:
{
    "task_id": 123,
    "image_path": "...",
    "regions": [
        {"bbox": [...], "text": "corrected text", "status": "accepted"}
    ],
    "completed_at": "2026-01-21T..."
}
```

**Storage:** JSON file (`/data/annotations.json`) for POC simplicity.

### 4. Python Client

**Functions:**
- `create_project(name, labeling_config)` - Set up new annotation project
- `configure_ml_backend(project_id, url)` - Connect Tesseract backend
- `configure_webhook(project_id, url)` - Set annotation webhook
- `create_task(project_id, image_path)` - Submit image for annotation
- `get_annotations(project_id)` - Retrieve completed annotations

---

## Implementation Steps

### Step 1: Docker Compose Setup
Create `docker-compose.yml` with all 4 services:
- Label Studio (extends existing App/compose.yml pattern)
- PostgreSQL
- Tesseract ML backend
- Webhook receiver

**Networking and startup order:**
- All services on same Docker network (`hitl-network`)
- Use `depends_on` with health checks:
  - PostgreSQL starts first (Label Studio depends on it)
  - Label Studio starts second (ML backend and webhook depend on it)
  - ML backend and webhook receiver start last
- ML backend env: `LABEL_STUDIO_URL=http://labelstudio:8080`
- ML backend should retry Label Studio connection on startup (may not be ready immediately)

### Step 2: Tesseract ML Backend
- Create Dockerfile with pytesseract + tesseract-ocr
- Implement `model.py` with Label Studio ML backend protocol
- Implement `ocr_processor.py` with confidence scoring

### Step 3: Labeling Configuration
- Create `labeling_config.xml` with Image + RectangleLabels + TextArea + Choices
- Configure confidence-based styling

### Step 4: Webhook Receiver
- Create FastAPI app with annotation endpoint
- Implement JSON storage
- Add query endpoint

### Step 5: Python Client
- Create `label_studio_client.py` with SDK wrapper functions
- Implement project setup and task submission

### Step 6: Setup Scripts
- `setup_project.py` - One-time project creation and configuration
- `submit_sample_tasks.py` - Demo script using test images

---

## Verification

**Setup:**
```bash
docker-compose up -d
python scripts/setup_project.py
python scripts/submit_sample_tasks.py
```

**Checklist:**
- [ ] Label Studio UI accessible at http://localhost:8080
- [ ] Log in, see project with test images
- [ ] Images show pre-annotated OCR bounding boxes with text
- [ ] Can adjust bounding boxes, edit text, select accept/reject per region
- [ ] Data Manager shows prediction scores, can filter/sort by score
- [ ] On submit, webhook receiver logs the annotation
- [ ] GET /annotations returns stored corrections

**Test scenarios:**
1. Clear image → high confidence, minimal flagging
2. Blurry/rotated image → low confidence regions flagged
3. Correct text, submit → webhook receives corrected data

---

## Acceptance Criteria Mapping

| Criteria | Implementation |
|----------|----------------|
| Local Label Studio running | Docker Compose with Label Studio + PostgreSQL |
| API creates annotation tasks | `label_studio_client.py` + `submit_sample_tasks.py` |
| Webhook captures annotations | FastAPI receiver at port 8000 |
| Test with sample documents | `images/` folder + `submit_sample_tasks.py` |

---

## Key Files to Create

1. `HITL/docker-compose.yml`
2. `HITL/.env`
3. `HITL/ml_backend/Dockerfile`
4. `HITL/ml_backend/requirements.txt`
5. `HITL/ml_backend/model.py`
6. `HITL/ml_backend/ocr_processor.py`
7. `HITL/webhook_receiver/Dockerfile`
8. `HITL/webhook_receiver/requirements.txt`
9. `HITL/webhook_receiver/main.py`
10. `HITL/client/requirements.txt`
11. `HITL/client/label_studio_client.py`
12. `HITL/config/labeling_config.xml`
13. `HITL/scripts/setup_project.py`
14. `HITL/scripts/submit_sample_tasks.py`
