# ======================================================================
# Dockerfile para Huellas Paisas API
# Imagen slim para reducir tamaño, sin multi-stage para mantener
# la simplicidad del taller. Si se quiere optimizar más, se puede
# separar en etapas "builder" y "runtime".
# ======================================================================

FROM python:3.11-slim

# Evita que Python escriba .pyc y fuerza stdout/stderr sin buffer
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Instalamos dependencias del sistema necesarias para algunas libs.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Copiamos primero los requirements para aprovechar la cache de layers.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código fuente.
COPY src/ ./src/
COPY pyproject.toml .

# Carpeta para la base de datos SQLite persistente.
RUN mkdir -p /app/data

EXPOSE 8000

# Healthcheck sencillo contra el endpoint /health.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.infrastructure.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
