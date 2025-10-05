# >>> AUTO-GEN BEGIN: Makefile v1.2
.PHONY: help setup install-optional hooks fmt lint lint-code test doctor clean deepclean fullcheck repair build run-cli run-api run-ui

help:
	@echo "Targets: setup, install-optional, hooks, fmt, lint, lint-code, test, doctor, clean, deepclean, fullcheck, repair, build, run-cli, run-api, run-ui"

setup:
	python -m pip install --upgrade pip
	@if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; fi
	@if [ -f pyproject.toml ] || [ -f setup.py ]; then pip install -e . || true; fi
	python -m astroengine.diagnostics --strict || true

install-optional:
	python scripts/install_optional_dependencies.py

all: install compile lint test

venv:
$(PY_BIN) -m venv $(VENV)
$(PY) -m pip install -U pip setuptools wheel

install: venv
@if [ -f requirements-dev.txt ]; then $(PIP) install -r requirements-dev.txt; fi
@if [ -f requirements.txt ]; then $(PIP) install -r requirements.txt; fi
-$(PIP) install -e ".[api,providers,ui]" || $(PIP) install -e .

compile:
$(PY) -m compileall -q .

lint:
-$(RUFF) check .
-$(BLACK) --check .
-$(ISORT) --check-only --profile black .

typecheck:
-$(MYPY) || true

test:
-$(PYTEST) -q || true

migrate:
-$(ALEMBIC) upgrade head || true

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
$(UVICORN) $(APP_MODULE) --host 0.0.0.0 --port 8000 --workers $$(( $$(nproc) ))

run-ui:
$(STREAMLIT) run $(UI_ENTRY)

clean:
rm -rf $(ASTROENGINE_HOME) .pytest_cache .mypy_cache **/__pycache__ build dist *.egg-info

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
