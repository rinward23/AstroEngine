SHELL := /bin/bash
PY_BIN ?= python3.11
VENV := .venv
PIP := $(VENV)/bin/pip
PY := $(VENV)/bin/python
UVICORN := $(VENV)/bin/uvicorn
STREAMLIT := $(VENV)/bin/streamlit
RUFF := $(VENV)/bin/ruff
BLACK := $(VENV)/bin/black
ISORT := $(VENV)/bin/isort
MYPY := $(VENV)/bin/mypy
PYTEST := $(VENV)/bin/pytest
ALEMBIC := $(VENV)/bin/alembic

APP_MODULE ?= app.main:app
UI_ENTRY ?= ui/streamlit/vedic_app.py
DB_URL ?= sqlite:///./dev.db
ASTROENGINE_HOME ?= ./.astroengine
SE_EPHE_PATH ?=
AE_WARM_BODIES ?= sun,moon,mercury,venus,mars,jupiter,saturn
AE_WARM_START ?= 2000-01-01
AE_WARM_END ?= 2030-12-31

export DB_URL ASTROENGINE_HOME SE_EPHE_PATH AE_WARM_BODIES AE_WARM_START AE_WARM_END

.PHONY: all venv install dev compile lint typecheck test migrate cache-warm doctor run-cli run-api run-ui clean deepclean

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
$(PY) - <<PY
from os import getenv
bodies=getenv("AE_WARM_BODIES","sun,moon").split(",")
start=getenv("AE_WARM_START","2000-01-01")
end=getenv("AE_WARM_END","2030-12-31")
try:
    from astroengine.legacy.cache import warm as warm_cache
    warm_cache(bodies=bodies, start=start, end=end)
    print("Cache warmed", bodies)
except Exception as e:
    print("Cache warm skipped:", e)
PY

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

deepclean: clean
rm -rf $(VENV)
