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
