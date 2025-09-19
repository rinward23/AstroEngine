# >>> AUTO-GEN BEGIN: AstroEngine Dev Setup (bash) v1.0
#!/usr/bin/env bash
set -euo pipefail

if command -v conda >/dev/null 2>&1; then
  echo "[setup] Creating/updating conda env 'astroengine'..."
  conda env update -f environment.yml --prune
  echo "[setup] Activate with: conda activate astroengine"
else
  echo "[setup] Using venv + pip (conda not found)"
  python -m venv .venv
  . .venv/bin/activate
  pip install --upgrade pip
  if [ -f pyproject.toml ]; then
    pip install -e .[dev,api,charts,locational,fallback-ephemeris]
  else
    pip install -r requirements.txt
  fi
fi

python scripts/swe_smoketest.py || true
# >>> AUTO-GEN END: AstroEngine Dev Setup (bash) v1.0
