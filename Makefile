# >>> AUTO-GEN BEGIN: Makefile v1.2
.PHONY: help setup install-optional hooks fmt lint lint-code test doctor clean deepclean fullcheck repair build

help:
	@echo "Targets: setup, install-optional, hooks, fmt, lint, lint-code, test, doctor, clean, deepclean, fullcheck, repair, build"

setup:
	python -m pip install --upgrade pip
	@if [ -f requirements-dev.txt ]; then PIP_CONSTRAINT=constraints.txt pip install -r requirements-dev.txt; fi
	@if [ -f pyproject.toml ] || [ -f setup.py ]; then PIP_CONSTRAINT=constraints.txt pip install -e . || true; fi
	python -m astroengine.diagnostics --strict || true

install-optional:
	python scripts/install_optional_dependencies.py

hooks:
	python -m pip install -U pre-commit
	python -m pre_commit install-hooks

fmt:
	ruff check --fix . || true
	black . || true
	isort --profile=black . || true

lint:
	python -m pre_commit run --all-files

lint-code:
	ruff check .
	black --check .
	isort --check-only --profile=black .

test:
	# Ensure test dependencies are installed before running pytest
	python scripts/install_test_dependencies.py --quiet
	pytest -q

doctor:
	python -m astroengine.diagnostics || true
	python -m astroengine.diagnostics --strict

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache build dist *.egg-info **/__pycache__
	@[ -f diagnostics.json ] && rm -f diagnostics.json || true

deepclean:
	python scripts/cleanup/repo_clean.py --deep

fullcheck:
	python -m astroengine.maint --full --strict || true

repair:
	python -m astroengine.maint --full --strict --auto-install all --yes --with-tests || true

build:
	python -m astroengine.maint --with-build || true
# >>> AUTO-GEN END: Makefile v1.2
