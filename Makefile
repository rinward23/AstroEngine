# >>> AUTO-GEN BEGIN: Makefile v1.1
.PHONY: help setup fmt lint test doctor clean fullcheck repair build

help:
	@echo "Targets: setup, fmt, lint, test, doctor, clean, fullcheck, repair, build"

setup:
	python -m pip install --upgrade pip
	@if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; fi
	@if [ -f pyproject.toml ] || [ -f setup.py ]; then pip install -e . || true; fi
	@which pre-commit >/dev/null 2>&1 && pre-commit install || true

fmt:
	ruff check --fix . || true
	black . || true
	isort --profile=black . || true

lint:
	ruff check .
	black --check .
	isort --check-only --profile=black .

test:
	pytest -q

doctor:
	python -m astroengine.diagnostics || true
	python -m astroengine.diagnostics --strict

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache build dist *.egg-info **/__pycache__
	@[ -f diagnostics.json ] && rm -f diagnostics.json || true

fullcheck:
	python -m astroengine.maint --full --strict || true

repair:
	python -m astroengine.maint --full --strict --auto-install all --yes --with-tests || true

build:
	python -m astroengine.maint --with-build || true
# >>> AUTO-GEN END: Makefile v1.1
