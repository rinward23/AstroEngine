#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python -m pip install --upgrade pip

if [[ -f "${PROJECT_ROOT}/requirements.txt" ]]; then
  pip install -r "${PROJECT_ROOT}/requirements.txt"
fi

if [[ -f "${PROJECT_ROOT}/requirements-dev.txt" ]]; then
  pip install -r "${PROJECT_ROOT}/requirements-dev.txt"
fi

if [[ -f "${PROJECT_ROOT}/pyproject.toml" ]] || [[ -f "${PROJECT_ROOT}/setup.py" ]]; then
  pip install -e "${PROJECT_ROOT}" || true
fi

