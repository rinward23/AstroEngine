# AstroEngine runtime + tooling image
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    SE_EPHE_PATH=/opt/ephe \
    LOG_LEVEL=INFO

ARG APP_HOME=/workspace
WORKDIR ${APP_HOME}

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system astro && useradd --system --create-home --gid astro astro

COPY . ${APP_HOME}

RUN python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir . \
    && python -m pip install --no-cache-dir '.[tools]' \
    && mkdir -p /opt/ephe /data /licenses \
    && cp LICENSE /licenses/ \
    && if [ -f NOTICE ]; then cp NOTICE /licenses/; fi \
    && chown -R astro:astro ${APP_HOME} /opt/ephe /data /licenses

USER astro

EXPOSE 8000 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 CMD curl -fsS http://127.0.0.1:8000/healthz || exit 1

CMD ["astroengine-api"]
