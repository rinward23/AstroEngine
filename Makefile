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
	python -m pip install --upgrade pip
	@if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; fi
	@if [ -f pyproject.toml ] || [ -f setup.py ]; then pip install -e ".[api,providers,ui]" || pip install -e .; fi
	python -m astroengine.diagnostics --strict || true

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
	@:

doctor:
$(PY) - <<PY
try:
    import astroengine
    print("astroengine OK")
except Exception as e:
    print("astroengine import failed:", e)
PY

run-cli:
$(PY) -m astroengine --help || true

run-api:
>$(UVICORN) $(APP_MODULE) --host $(API_HOST) --port $(API_PORT) --reload

run-ui:
>$(STREAMLIT) run $(UI_ENTRY) --server.address 0.0.0.0 --server.port 8501

clean:
>rm -rf .mypy_cache .pytest_cache **/__pycache__ dist build *.egg-info

build:
	python -m astroengine.maint --with-build || true

run-cli: install-optional
	python -m astroengine --help

run-api: install-optional
	uvicorn app.main:app --host 127.0.0.1 --port 8000

run-ui: install-optional
	streamlit run ui/streamlit/altaz_app.py --server.port 8501 --server.address 0.0.0.0
# >>> AUTO-GEN END: Makefile v1.2

# Custom operational helpers
.PHONY: migrate cache-warm

migrate:
	.venv/bin/alembic upgrade head

cache-warm:
	AE_WARM_START=$${AE_WARM_START:-1900-01-01} \
	AE_WARM_END=$${AE_WARM_END:-2100-12-31} \
	python -m astroengine.pipeline.cache_warm
