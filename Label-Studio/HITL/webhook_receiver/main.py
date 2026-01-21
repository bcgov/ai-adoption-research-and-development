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
