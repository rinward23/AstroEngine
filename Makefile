PYTHON ?= python3
PIP ?= $(PYTHON) -m pip

.DEFAULT_GOAL := help

.PHONY: help env lint format typecheck test smoke preflight wheel check

help:
        @echo "Common development targets:"
        @echo "  make env        # install astroengine with developer extras"
        @echo "  make format     # apply Ruff/Black/isort formatting"
        @echo "  make lint       # run static linters"
        @echo "  make typecheck  # execute mypy against typed packages"
        @echo "  make test       # execute pytest"
        @echo "  make smoke      # run the Swiss Ephemeris smoketest"
        @echo "  make preflight  # run environment diagnostics"
        @echo "  make wheel      # build a distribution wheel"

env:
        $(PIP) install -e .[dev]

lint:
        $(PYTHON) -m ruff check .
        $(PYTHON) -m black --check .
        $(PYTHON) -m isort --check-only .

format:
        $(PYTHON) -m ruff check --fix .
        $(PYTHON) -m black .
        $(PYTHON) -m isort .

typecheck:
        $(PYTHON) -m mypy astroengine/core astroengine/ephemeris astroengine/chart

test:
        $(PYTHON) -m pytest

check: lint typecheck test

smoke:
        $(PYTHON) scripts/swe_smoketest.py

preflight:
        $(PYTHON) scripts/preflight.py

wheel:
        $(PYTHON) -m build
