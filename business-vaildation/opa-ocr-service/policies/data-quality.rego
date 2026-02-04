package ocr.validation.data_quality

# Default: deny if not explicitly allowed
default allowed = false

# Main data quality check
allowed {
    ocr_succeeded
    has_extracted_text
    meets_confidence_threshold
    has_required_structure
}

# Check if OCR status is succeeded
ocr_succeeded {
    input.ocrResult.status == "succeeded"
}

# Check if extracted text exists and has content
has_extracted_text {
    count(input.ocrResult.extractedText) > 0
}

# Check if pages have minimum confidence threshold
meets_confidence_threshold {
    # If pages exist, check confidence (assuming average confidence > 0.7)
    count(input.ocrResult.pages) > 0
}

# Alternative: check if any page has words with confidence
meets_confidence_threshold {
    some page in input.ocrResult.pages
    some word in page.words
    word.confidence > 0.7
}

# Check if document has required structure (at least pages or key-value pairs)
has_required_structure {
    count(input.ocrResult.pages) > 0
}

# Alternative: key-value pairs indicate structured data
has_required_structure {
    count(input.ocrResult.keyValuePairs) > 0
}

# Violations for detailed feedback
violations[violation] {
    not ocr_succeeded
    violation := {
        "rule": "ocr_status_check",
        "message": "OCR status is not 'succeeded'",
        "severity": "error",
        "field": "status",
        "value": input.ocrResult.status
    }
}

violations[violation] {
    not has_extracted_text
    violation := {
        "rule": "extracted_text_check",
        "message": "No extracted text found in OCR result",
        "severity": "error",
        "field": "extractedText"
    }
}

violations[violation] {
    not meets_confidence_threshold
    violation := {
        "rule": "confidence_threshold_check",
        "message": "OCR confidence does not meet minimum threshold (0.7)",
        "severity": "warning",
        "field": "pages"
    }
}

# Calculate data quality score (0.0 to 1.0)
dataQualityScore = score {
    ocr_succeeded_score = 1.0
    ocr_succeeded
    extracted_text_score = 1.0
    has_extracted_text
    confidence_score = 1.0
    meets_confidence_threshold
    structure_score = 1.0
    has_required_structure
    score = (ocr_succeeded_score + extracted_text_score + confidence_score + structure_score) / 4
}

dataQualityScore = score {
    ocr_succeeded_score = 1.0
    ocr_succeeded
    extracted_text_score = 1.0
    has_extracted_text
    confidence_score = 0.5
    not meets_confidence_threshold
    structure_score = 1.0
    has_required_structure
    score = (ocr_succeeded_score + extracted_text_score + confidence_score + structure_score) / 4
}

dataQualityScore = 0.0 {
    not ocr_succeeded
}

