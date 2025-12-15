"""Configuration constants for template processing and OCR."""

# Configure ROI padding (adds margin around extraction zones to prevent edge clipping)
# Recommended: 10-20 pixels for handwritten text, 5-10 for printed text
ROI_PADDING = 15  # Adjust this value to add more/less padding around OCR zones

# OCR detector tuning (aligned to slice debug settings)
DET_DB_THRESH = 0.3            # Lower = more sensitive to faint text
DET_DB_BOX_THRESH = 0.5        # Stricter box filtering
DET_DB_UNCLIP_RATIO = 2.0      # Box expansion ratio (higher to reduce truncation)
DET_LIMIT_SIDE_LEN = 2000      # Input size limit (match slice test)
DET_LIMIT_TYPE = "max"
USE_DOC_ORIENTATION_CLASSIFY = False
USE_DOC_UNWARPING = False
USE_TEXTLINE_ORIENTATION = True
