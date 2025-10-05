.PHONY: help setup install-optional fmt lint typecheck test doctor migrate cache-warm run-api run-ui clean build
.RECIPEPREFIX := >

PYTHON ?= python
PIP ?= $(PYTHON) -m pip
UVICORN ?= uvicorn
STREAMLIT ?= streamlit
ALEMBIC ?= alembic
APP_MODULE ?= app.main:app
UI_ENTRY ?= ui/streamlit/altaz_app.py
API_HOST ?= 0.0.0.0
API_PORT ?= 8000

help:
>@echo "Common developer targets:"
>@echo "  make setup           # install runtime + dev dependencies"
>@echo "  make doctor          # strict environment diagnostics"
>@echo "  make run-api         # launch FastAPI service on $(API_HOST):$(API_PORT)"
>@echo "  make run-ui          # launch Streamlit UI"
>@echo "  make cache-warm      # warm ephemeris cache with real data"
>@echo "  make migrate         # apply latest database migrations"
>@echo "  make test            # run pytest suite"

setup:
>$(PYTHON) -m pip install --upgrade pip
>@if [ -f requirements.txt ]; then $(PIP) install -r requirements.txt; fi
>@if [ -f requirements-dev.txt ]; then $(PIP) install -r requirements-dev.txt; fi
>$(PIP) install -e ".[api,providers,ui]" || $(PIP) install -e .

install-optional:
>$(PYTHON) scripts/install_optional_dependencies.py

fmt:
>ruff check --select I --fix .
>black .
>isort --profile black .

lint:
>ruff check .
>black --check .
>isort --check-only --profile black .

typecheck:
>mypy .

test:
>pytest -q

doctor:
>$(PYTHON) -m astroengine.diagnostics --strict

migrate:
>$(ALEMBIC) upgrade head

cache-warm:
>$(PYTHON) -m astroengine.pipeline.cache_warm

run-api:
>$(UVICORN) $(APP_MODULE) --host $(API_HOST) --port $(API_PORT) --reload

run-ui:
>$(STREAMLIT) run $(UI_ENTRY) --server.address 0.0.0.0 --server.port 8501

clean:
>rm -rf .mypy_cache .pytest_cache **/__pycache__ dist build *.egg-info

build:
>$(PYTHON) -m build
