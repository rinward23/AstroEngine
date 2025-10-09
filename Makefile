.PHONY: help setup install-optional fmt lint typecheck test doctor doctor-lite migrate cache-warm run-cli run-api run-ui clean build

SHELL := /bin/bash

PYTHON ?= python
PIP ?= $(PYTHON) -m pip
UVICORN ?= uvicorn
STREAMLIT ?= streamlit
ALEMBIC ?= alembic
ENV_EXPORT ?= if [ -f .env ]; then set -a; source ./.env; set +a; fi
APP_MODULE ?= app.main:app
UI_ENTRY ?= ui/streamlit/altaz_app.py
API_HOST ?= 0.0.0.0
API_PORT ?= 8000

help:
	@echo "Common developer targets:"
	@echo "  make setup           # install runtime + dev dependencies"
	@echo "  make doctor          # strict environment diagnostics"
	@echo "  make run-api         # launch FastAPI service on $(API_HOST):$(API_PORT)"
	@echo "  make run-ui          # launch Streamlit UI"
	@echo "  make cache-warm      # warm ephemeris cache with real data"
	@echo "  make migrate         # apply latest database migrations"
	@echo "  make test            # run pytest suite"

setup:
        $(PYTHON) -m pip install --upgrade pip
        @if [ -f requirements/base.txt ]; then pip install -r requirements/base.txt; fi
        @if [ -f requirements/dev.txt ]; then pip install -r requirements/dev.txt; fi
        @if [ -f pyproject.toml ] || [ -f setup.py ]; then pip install -e ".[api,providers,ui]" || pip install -e .; fi
        $(PYTHON) -m astroengine.diagnostics --strict || true

install-optional:
	$(PYTHON) scripts/install_optional_dependencies.py

fmt:
	ruff check --select I --fix .
	black .
	isort --profile black .

lint:
	ruff check .
	black --check .
	isort --check-only --profile black .

typecheck:
	mypy .

test:
	pytest -q

doctor:
	$(PYTHON) -m astroengine.diagnostics --strict

doctor-lite:
	$(PYTHON) - <<-'PYCODE'
	try:
	    import astroengine
	    print("astroengine OK")
	except Exception as exc:
	    print("astroengine import failed:", exc)
	PYCODE

migrate:
	$(ENV_EXPORT) && $(ALEMBIC) upgrade head

cache-warm:
	$(ENV_EXPORT) && AE_WARM_START=$${AE_WARM_START:-1900-01-01} \\
	AE_WARM_END=$${AE_WARM_END:-2100-12-31} \\
	$(PYTHON) -m astroengine.pipeline.cache_warm

run-cli: install-optional
	$(ENV_EXPORT) && $(PYTHON) -m astroengine --help || true

run-api: install-optional
	$(ENV_EXPORT) && $(UVICORN) $(APP_MODULE) --host $(API_HOST) --port $(API_PORT) --reload

run-ui: install-optional
	$(ENV_EXPORT) && $(STREAMLIT) run $(UI_ENTRY) --server.address 0.0.0.0 --server.port 8501

clean:
	rm -rf .mypy_cache .pytest_cache **/__pycache__ dist build *.egg-info

build:
	$(PYTHON) -m astroengine.maint --with-build || true
