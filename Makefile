PYTHON ?= python3
PIP ?= $(PYTHON) -m pip

.PHONY: env lint format test smoke wheel preflight

env:
	$(PIP) install -e .[dev]

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m black --check .
	$(PYTHON) -m isort --check-only .
	$(PYTHON) -m mypy astroengine/core astroengine/ephemeris astroengine/chart

format:
	$(PYTHON) -m ruff check --fix .
	$(PYTHON) -m black .
	$(PYTHON) -m isort .

test:
	$(PYTHON) -m pytest

smoke:
	$(PYTHON) scripts/swe_smoketest.py

preflight:
	$(PYTHON) scripts/preflight.py

wheel:
	$(PYTHON) -m build
