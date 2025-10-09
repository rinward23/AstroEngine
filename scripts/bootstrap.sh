#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python -m pip install --upgrade pip

if [[ -f "${PROJECT_ROOT}/requirements/base.txt" ]]; then
  pip install -r "${PROJECT_ROOT}/requirements/base.txt"
fi

if [[ -f "${PROJECT_ROOT}/requirements/dev.txt" ]]; then
  pip install -r "${PROJECT_ROOT}/requirements/dev.txt"
fi

if [[ -f "${PROJECT_ROOT}/pyproject.toml" ]] || [[ -f "${PROJECT_ROOT}/setup.py" ]]; then
  pushd "${PROJECT_ROOT}" >/dev/null
  # API + providers + UI in one go (fallback to core only if extras unavailable)
  pip install -e ".[api,providers,ui]" || pip install -e .
  popd >/dev/null
fi

