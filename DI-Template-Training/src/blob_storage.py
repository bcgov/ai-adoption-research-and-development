"""Azure Blob Storage utilities for training data management."""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from azure.storage.blob import (
    BlobServiceClient,
    ContainerSasPermissions,
    generate_container_sas,
)

from .utils import print_progress


def ensure_container_exists(
    client: BlobServiceClient,
    container_name: str,
) -> bool:
    """
    Ensure a blob container exists, creating it if necessary.

    Args:
        client: BlobServiceClient instance
        container_name: Name of the container

    Returns:
        True if container was created, False if it already existed
    """
    container_client = client.get_container_client(container_name)
    try:
        container_client.get_container_properties()
        return False  # Already exists
    except Exception:
        container_client.create_container()
        return True  # Created


def upload_file_to_blob(
    client: BlobServiceClient,
    container_name: str,
    local_path: Path | str,
    blob_name: Optional[str] = None,
    overwrite: bool = True,
) -> str:
    """
    Upload a single file to blob storage.

    Args:
        client: BlobServiceClient instance
        container_name: Target container name
        local_path: Local file path
        blob_name: Name in blob storage (defaults to filename)
        overwrite: Whether to overwrite existing blobs

    Returns:
        Blob URL
    """
    local_path = Path(local_path)
    blob_name = blob_name or local_path.name

    container_client = client.get_container_client(container_name)
    blob_client = container_client.get_blob_client(blob_name)

    with open(local_path, "rb") as f:
        blob_client.upload_blob(f, overwrite=overwrite)

    return blob_client.url


def upload_training_data(
    client: BlobServiceClient,
    container_name: str,
    training_dir: Path | str,
    verbose: bool = True,
) -> dict:
    """
    Upload all training data files to blob storage.

    Expected files in training_dir:
    - fields.json
    - *.jpg (training images)
    - *.jpg.ocr.json (OCR output for each image)
    - *.jpg.labels.json (labels for each image)

    Args:
        client: BlobServiceClient instance
        container_name: Target container name
        training_dir: Directory containing training data
        verbose: Print progress

    Returns:
        Dict with upload statistics
    """
    training_dir = Path(training_dir)

    # Ensure container exists
    created = ensure_container_exists(client, container_name)
    if verbose and created:
        print(f"Created container: {container_name}")

    # Find all files to upload
    files_to_upload = []

    # fields.json (required)
    fields_json = training_dir / "fields.json"
    if fields_json.exists():
        files_to_upload.append(fields_json)
    else:
        raise FileNotFoundError(f"fields.json not found in {training_dir}")

    # Training images and their associated files
    for img_path in training_dir.glob("*.jpg"):
        files_to_upload.append(img_path)

        # OCR JSON
        ocr_path = img_path.parent / f"{img_path.name}.ocr.json"
        if ocr_path.exists():
            files_to_upload.append(ocr_path)

        # Labels JSON
        labels_path = img_path.parent / f"{img_path.name}.labels.json"
        if labels_path.exists():
            files_to_upload.append(labels_path)

    # Upload all files
    uploaded = []
    failed = []

    for i, file_path in enumerate(files_to_upload):
        if verbose:
            print_progress(i + 1, len(files_to_upload), "Uploading")

        try:
            url = upload_file_to_blob(client, container_name, file_path)
            uploaded.append({"file": file_path.name, "url": url})
        except Exception as e:
            failed.append({"file": file_path.name, "error": str(e)})

    return {
        "container": container_name,
        "total_files": len(files_to_upload),
        "uploaded": len(uploaded),
        "failed": len(failed),
        "uploaded_files": uploaded,
        "failed_files": failed,
    }


def generate_sas_url(
    client: BlobServiceClient,
    container_name: str,
    expiry_days: int = 7,
) -> str:
    """
    Generate a SAS URL for a container.

    Args:
        client: BlobServiceClient instance
        container_name: Container name
        expiry_days: Number of days until SAS expires

    Returns:
        Full container URL with SAS token
    """
    # Get account details from client
    account_name = client.account_name
    account_key = client.credential.account_key

    # Generate SAS token
    sas_token = generate_container_sas(
        account_name=account_name,
        container_name=container_name,
        account_key=account_key,
        permission=ContainerSasPermissions(read=True, list=True),
        expiry=datetime.now(timezone.utc) + timedelta(days=expiry_days),
    )

    # Build full URL
    container_client = client.get_container_client(container_name)
    return f"{container_client.url}?{sas_token}"


def list_container_blobs(
    client: BlobServiceClient,
    container_name: str,
    prefix: Optional[str] = None,
) -> list[dict]:
    """
    List blobs in a container.

    Args:
        client: BlobServiceClient instance
        container_name: Container name
        prefix: Optional prefix filter

    Returns:
        List of blob info dicts
    """
    container_client = client.get_container_client(container_name)

    blobs = []
    for blob in container_client.list_blobs(name_starts_with=prefix):
        blobs.append({
            "name": blob.name,
            "size": blob.size,
            "last_modified": blob.last_modified,
            "content_type": blob.content_settings.content_type if blob.content_settings else None,
        })

    return blobs


def delete_container_contents(
    client: BlobServiceClient,
    container_name: str,
    prefix: Optional[str] = None,
    verbose: bool = True,
) -> int:
    """
    Delete all blobs in a container (or with a prefix).

    Args:
        client: BlobServiceClient instance
        container_name: Container name
        prefix: Optional prefix to filter blobs
        verbose: Print progress

    Returns:
        Number of blobs deleted
    """
    container_client = client.get_container_client(container_name)

    blobs = list(container_client.list_blobs(name_starts_with=prefix))

    for i, blob in enumerate(blobs):
        if verbose:
            print_progress(i + 1, len(blobs), "Deleting")
        container_client.delete_blob(blob.name)

    return len(blobs)
