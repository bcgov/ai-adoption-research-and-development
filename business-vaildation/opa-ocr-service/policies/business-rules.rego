package ocr.validation.business_rules

# Default: deny if not explicitly allowed
default allowed = false

# Main business rules check
allowed {
    has_required_fields
    valid_document_type
    valid_file_metadata
}

# Check if document has required fields based on key-value pairs
has_required_fields {
    count(input.ocrResult.keyValuePairs) > 0
}

# Alternative: check if extracted text contains meaningful content
has_required_fields {
    count(input.ocrResult.extractedText) > 50  # At least 50 characters
}

# Validate document type based on file extension
valid_document_type {
    input.ocrResult.fileType in ["pdf", "image", "png", "jpg", "jpeg"]
}

# Check file metadata
valid_file_metadata {
    input.ocrResult.fileName != ""
    input.ocrResult.processedAt != ""
}

# Violations for detailed feedback
violations[violation] {
    not has_required_fields
    violation := {
        "rule": "required_fields_check",
        "message": "Document does not contain required fields or sufficient content",
        "severity": "error",
        "field": "keyValuePairs"
    }
}

violations[violation] {
    not valid_document_type
    violation := {
        "rule": "document_type_check",
        "message": "Invalid document type. Allowed types: pdf, image, png, jpg, jpeg",
        "severity": "error",
        "field": "fileType",
        "value": input.ocrResult.fileType
    }
}

violations[violation] {
    not valid_file_metadata
    violation := {
        "rule": "file_metadata_check",
        "message": "Missing required file metadata (fileName or processedAt)",
        "severity": "error",
        "field": "metadata"
    }
}

# Business rule compliance flag
businessRuleCompliance = true {
    has_required_fields
    valid_document_type
    valid_file_metadata
}

businessRuleCompliance = false {
    not has_required_fields
}

businessRuleCompliance = false {
    not valid_document_type
}

businessRuleCompliance = false {
    not valid_file_metadata
}

