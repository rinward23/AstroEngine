# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    AE_QCACHE_SEC=0.25 \
    AE_QCACHE_SIZE=16384

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY astroengine ./astroengine
COPY app ./app

# Install with API+provider extras
RUN pip install -U pip && \
    pip install ".[api,providers]" "uvicorn[standard]"

# Optional: ship Swiss ephemeris files in-image
# COPY eph/ /opt/eph/
# ENV SE_EPHE_PATH=/opt/eph

# Non-root user
RUN useradd -r -u 10001 astro && chown -R astro:astro /app
USER astro

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/health/plus || exit 1

CMD ["python", "-m", "app.uvicorn_runner"]
