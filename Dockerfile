# Multi-purpose image: CLI + API + (optional) UI
FROM python:3.11-slim AS base

ARG EXTRA_GROUPS="api,providers"
ENV ASTROENGINE_EXTRAS="${EXTRA_GROUPS}"
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    AE_QCACHE_SEC=0.25 \
    AE_QCACHE_SIZE=16384

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps (build tools for any native wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install requested extras (defaults to API + providers)
RUN set -eux; \
    pip install -U pip; \
    if [ -n "${ASTROENGINE_EXTRAS}" ]; then \
        pip install ".[${ASTROENGINE_EXTRAS}]"; \
    else \
        pip install .; \
    fi; \
    if printf '%s' "${ASTROENGINE_EXTRAS}" | grep -q "api"; then \
        pip install "uvicorn[standard]"; \
    fi

# Runtime env
ENV DATABASE_URL="sqlite:///./dev.db" \
    ASTROENGINE_HOME="/app/.astroengine" \
    AE_QCACHE_SIZE=4096 AE_QCACHE_SEC=1.0

# Create cache directory
RUN mkdir -p "$ASTROENGINE_HOME"

# Expose API port
EXPOSE 8000

CMD ["python", "-m", "app.uvicorn_runner"]
