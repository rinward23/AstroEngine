# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

ARG EXTRA_GROUPS="api,providers"
ENV ASTROENGINE_EXTRAS="${EXTRA_GROUPS}"
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY astroengine ./astroengine
COPY app ./app

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

# Optional: ship Swiss ephemeris files in-image
# COPY eph/ /opt/eph/
# ENV SE_EPHE_PATH=/opt/eph

# Non-root user
RUN useradd -r -u 10001 astro && chown -R astro:astro /app
USER astro

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/health/plus || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
