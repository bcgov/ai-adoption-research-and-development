"""DI-Template-Training source modules."""

from .utils import (
    load_image,
    save_image,
    load_json,
    save_json,
    ensure_dir,
    get_project_root,
)
from .alignment_wrapper import (
    get_alignment_config,
    align_image_to_template,
    AlignmentMode,
)
from .azure_client import (
    get_document_intelligence_client,
    get_blob_service_client,
)
from .ocr_generator import (
    generate_ocr_json,
    generate_ocr_json_batch,
)
from .labels_generator import (
    generate_fields_json,
    generate_labels_json,
    generate_labels_batch,
)
from .blob_storage import (
    upload_training_data,
    generate_sas_url,
    list_container_blobs,
)

__all__ = [
    # utils
    "load_image",
    "save_image",
    "load_json",
    "save_json",
    "ensure_dir",
    "get_project_root",
    # alignment
    "get_alignment_config",
    "align_image_to_template",
    "AlignmentMode",
    # azure client
    "get_document_intelligence_client",
    "get_blob_service_client",
    # ocr generator
    "generate_ocr_json",
    "generate_ocr_json_batch",
    # labels generator
    "generate_fields_json",
    "generate_labels_json",
    "generate_labels_batch",
    # blob storage
    "upload_training_data",
    "generate_sas_url",
    "list_container_blobs",
]
