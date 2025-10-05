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
  pushd "${PROJECT_ROOT}" >/dev/null
  pip install -e ".[api,providers,ui]" || pip install -e .
  popd >/dev/null
fi

