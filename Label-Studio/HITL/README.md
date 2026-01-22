# HITL OCR Annotation System

A Human-in-the-Loop (HITL) system for reviewing and correcting low-confidence OCR results using Label Studio.

## Overview

This system provides an automated OCR pipeline with human review capabilities:

1. **Images** are submitted to Label Studio
2. **Tesseract OCR** runs automatically via ML backend, extracting text with confidence scores
3. **Low-confidence results** (< 75%) are flagged for human review
4. **Annotators** can accept, reject, or correct OCR results including bounding boxes
5. **Webhooks** notify downstream systems when annotations are completed

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Docker Network                           │
│                                                                 │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐    │
│  │  PostgreSQL  │────▶│ Label Studio │────▶│  ML Backend  │    │
│  │   (Database) │     │   (Web UI)   │     │ (Tesseract)  │    │
│  │   :5432      │     │   :8080      │     │   :9090      │    │
│  └──────────────┘     └──────┬───────┘     └──────────────┘    │
│                              │                                  │
│                              │ webhooks                         │
│                              ▼                                  │
│                       ┌──────────────┐                         │
│                       │   Webhook    │                         │
│                       │   Receiver   │                         │
│                       │   :8000      │                         │
│                       └──────────────┘                         │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

- Docker and Docker Compose
- Python 3.10+ (for running setup scripts)

## Quick Start

### 1. Start the Services

```bash
cd HITL
docker compose up -d
```

Wait for all services to become healthy (takes ~30-60 seconds):

```bash
docker compose ps
```

All services should show `(healthy)` status.

### 2. Install Python Dependencies

```bash
pip install requests python-dotenv
```

Or using uv:
```bash
uv venv .venv && source .venv/bin/activate && uv pip install requests python-dotenv
```

### 3. Get Your API Key

1. Open Label Studio at http://localhost:8080
2. Log in with credentials from `.env`:
   - Email: `admin@example.com`
   - Password: `changeme123`
3. Go to **Account & Settings** (click your avatar in top-right)
4. Copy the **Access Token**
5. Add it to your `.env` file:
   ```bash
   LABEL_STUDIO_API_KEY=your-token-here
   ```

### 4. Set Up the Project

Run the setup script (it reads the API key from `.env`):

```bash
source .venv/bin/activate  # if using venv
python scripts/setup_project.py
```

> **Note:** Label Studio's Personal Access Tokens are JWT refresh tokens. The client automatically exchanges them for short-lived access tokens.

This creates:
- A Label Studio project with the OCR labeling configuration
- ML backend connection for automatic OCR
- Webhook for annotation notifications

### 5. Submit Sample Tasks

```bash
python scripts/submit_sample_tasks.py
```

This submits any images in the `images/` directory as annotation tasks.

### 6. Start Annotating

Open the project URL shown in the output, or go to:
- http://localhost:8080/projects

## Directory Structure

```
HITL/
├── config/
│   └── labeling_config.xml    # Label Studio UI configuration
├── client/
│   └── label_studio_client.py # Python SDK wrapper
├── images/                     # Sample images (add yours here)
├── ml_backend/
│   ├── Dockerfile
│   ├── _wsgi.py               # WSGI entry point
│   ├── model.py               # Label Studio ML backend
│   ├── ocr_processor.py       # Tesseract OCR wrapper
│   └── requirements.txt
├── scripts/
│   ├── setup_project.py       # One-time project setup
│   └── submit_sample_tasks.py # Submit images for annotation
├── webhook_receiver/
│   ├── Dockerfile
│   ├── main.py                # FastAPI webhook handler
│   └── requirements.txt
├── docs/plans/                 # Design documentation
├── .env                        # Environment configuration
├── .env.example               # Template for .env
└── docker-compose.yml
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| Label Studio | 8080 | Web UI for annotation |
| ML Backend | 9090 | Tesseract OCR predictions |
| Webhook Receiver | 8000 | Captures completed annotations |
| PostgreSQL | 5432 | Database (internal) |

## Annotation Workflow

1. **Auto-OCR**: When a task loads, the ML backend runs Tesseract OCR
2. **Pre-annotation**: Detected text boxes appear with extracted text
3. **Review**: Each region shows:
   - Bounding box (adjustable)
   - Transcription text (editable)
   - Status choice: Accepted / Rejected / Needs Review
4. **Submit**: Save the annotation
5. **Webhook**: System notifies downstream services

## Filtering Low-Confidence Results

In Label Studio Data Manager:

1. Click **Filters**
2. Add filter: `predictions.score < 0.75`
3. This shows only tasks with low-confidence OCR

## API Endpoints

### Webhook Receiver

- `GET /health` - Health check
- `GET /annotations` - List captured annotations
- `GET /annotations/{task_id}` - Get annotation by task ID
- `POST /webhook/annotation` - Receives Label Studio webhooks

### ML Backend

- `GET /health` - Health check
- `POST /predict` - Run OCR on image (called by Label Studio)

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LABEL_STUDIO_API_KEY` | - | API token (required) |
| `LABEL_STUDIO_PORT` | 8080 | Label Studio web port |
| `LABEL_STUDIO_USERNAME` | admin@example.com | Initial admin email |
| `LABEL_STUDIO_PASSWORD` | changeme123 | Initial admin password |
| `CONFIDENCE_THRESHOLD` | 0.75 | OCR confidence threshold |
| `ML_BACKEND_PORT` | 9090 | ML backend port |
| `WEBHOOK_PORT` | 8000 | Webhook receiver port |

## Common Commands

```bash
# Start services
docker compose up -d

# View logs
docker compose logs -f

# View specific service logs
docker compose logs -f ml_backend

# Stop services
docker compose down

# Rebuild after code changes
docker compose up -d --build

# Reset everything (deletes data)
docker compose down -v
```

## Troubleshooting

### Services not starting
```bash
docker compose logs
```

### ML backend not connecting
1. Check it's healthy: `curl http://localhost:9090/health`
2. In Label Studio, go to Settings > Machine Learning and reconnect

### Webhook not receiving events
1. Check it's healthy: `curl http://localhost:8000/health`
2. View captured annotations: `curl http://localhost:8000/annotations`

### Images not loading
- Ensure images are in the `images/` directory
- Check file permissions
- Supported formats: `.jpg`, `.jpeg`, `.png`

## Adding Your Own Images

1. Place images in the `images/` directory
2. Run the submit script:
   ```bash
   python scripts/submit_sample_tasks.py
   ```

## Development

### Modifying the ML Backend

Edit files in `ml_backend/`, then rebuild:
```bash
docker compose up -d --build ml_backend
```

### Modifying the Webhook Receiver

Edit files in `webhook_receiver/`, then rebuild:
```bash
docker compose up -d --build webhook_receiver
```

### Changing the Labeling Interface

Edit `config/labeling_config.xml` and update the project in Label Studio settings.
