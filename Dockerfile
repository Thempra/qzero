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

# ── Usuario sin privilegios ────────────────────────────────────────────────
# checkov dockerfile.security.missing-user: sin USER el proceso corre como root
# y un fallo en la API da control del contenedor. La API sólo escucha en 8000
# (>1024) y escribe en los volúmenes de /app, así que no necesita privilegios.
#
# Los directorios se crean AQUÍ con el dueño correcto: cuando Docker monta un
# volumen con nombre vacío lo inicializa copiando contenido y permisos de la
# ruta de la imagen, así que el volumen nace escribible por qzero. Un volumen
# que ya exista de un despliegue anterior sigue siendo de root y hay que
# migrarlo una vez (`chown -R 10001:10001 <volumen>`) antes de actualizar.
RUN groupadd --gid 10001 qzero \
    && useradd --uid 10001 --gid qzero --home-dir /app \
       --shell /usr/sbin/nologin --no-create-home qzero \
    && mkdir -p /app/data/hub /app/models /app/results \
    && chown -R qzero:qzero /app/data /app/models /app/results

USER qzero

# Run API via uvicorn
CMD ["uvicorn", "qzero.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--log-level", "info"]
