# QZero API — Production Dockerfile for Coolify
# Quantum-Enhanced Threat Detection Platform v3.0.0

FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    tcpdump \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first (Docker layer caching)
COPY pyproject.toml requirements.txt requirements-dev.txt ./
COPY src/ ./src/

# Install the project (editable — keeps src/ layout)
RUN pip install --no-cache-dir -e ".[api]"

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENV QZERO_ENV=production
ENV PYTHONPATH=/app/src
ENV LOG_LEVEL=INFO

# Run API via uvicorn
CMD ["uvicorn", "qzero.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--log-level", "info"]
