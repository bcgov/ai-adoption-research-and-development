# HITL/ml_backend/Dockerfile
FROM python:3.11-slim

# Install Tesseract OCR and dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
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
COPY _wsgi.py .

# Expose port
EXPOSE 9090

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD curl -f http://localhost:9090/health || exit 1

# Start the ML backend server using gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:9090", "--workers", "1", "--threads", "4", "_wsgi:app"]
