# AstroEngine runtime + tooling image
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    SE_EPHE_PATH=/opt/ephe

WORKDIR /workspace

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
    && rm -rf /var/lib/apt/lists/*

COPY . /workspace

RUN python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir '.[tools]' \
    && mkdir -p /opt/ephe /licenses \
    && cp LICENSE /licenses/ \
    && if [ -f NOTICE ]; then cp NOTICE /licenses/; fi

EXPOSE 8000 8501

CMD ["python", "-m", "app.uvicorn_runner"]
