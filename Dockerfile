# Base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies (needed for some scientific packages)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
# Agregamos fastapi y uvicorn que no estaban en el requirements original
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir fastapi uvicorn python-multipart

# Copy project files
COPY . .

# Expose API port
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app
ENV QZERO_ENV=production

# Command to run the API
CMD ["python", "src/api.py"]
