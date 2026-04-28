# ─────────────────────────────────────
# Text-to-Video Studio — Dockerfile
# Multi-stage build for smaller image
# ─────────────────────────────────────

# Stage 1: Base
FROM python:3.12-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python deps
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy application code
COPY backend/ backend/
COPY frontend/ frontend/
COPY run.py .
COPY .env.example .env

# Create data directory
RUN mkdir -p data/tasks

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# Run
CMD ["python", "run.py"]
