# Multi-purpose image: CLI + API + (optional) UI
FROM python:3.11-slim AS base

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps (build tools for any native wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Pre-copy only deps metadata to leverage layer cache
COPY pyproject.toml* setup.cfg* setup.py* requirements*.txt ./.

# Install runtime/dev deps if present (best effort)
RUN python -m pip install -U pip setuptools wheel && \
    if [ -f requirements.txt ]; then pip install -r requirements.txt; fi && \
    if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt || true; fi

# Now copy source
COPY . .

# Install package with extras (fallback to core)
RUN pip install -e ".[api,providers,ui]" || pip install -e .

# Runtime env
ENV DB_URL="sqlite:///./dev.db" \
    ASTROENGINE_HOME="/app/.astroengine" \
    AE_QCACHE_SIZE=4096 AE_QCACHE_SEC=1.0

# Create cache directory
RUN mkdir -p "$ASTROENGINE_HOME"

# Expose API port
EXPOSE 8000

# Default command runs API; override for CLI/UI as needed
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
