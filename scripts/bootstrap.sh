#!/usr/bin/env bash
set -euo pipefail

# ===== Config (overridable via env) =====
PY_BIN="${PY_BIN:-python3.11}"  # require 3.11
APP_MODULE="${APP_MODULE:-app.main:app}"
UI_ENTRY="${UI_ENTRY:-ui/streamlit/vedic_app.py}"
DB_URL="${DB_URL:-sqlite:///./dev.db}"
ASTROENGINE_HOME="${ASTROENGINE_HOME:-$PWD/.astroengine}"
SE_EPHE_PATH="${SE_EPHE_PATH:-}"  # optional
AE_WARM_BODIES="${AE_WARM_BODIES:-sun,moon,mercury,venus,mars,jupiter,saturn}"
AE_WARM_START="${AE_WARM_START:-2000-01-01}"
AE_WARM_END="${AE_WARM_END:-2030-12-31}"
AE_QCACHE_SIZE="${AE_QCACHE_SIZE:-4096}"
AE_QCACHE_SEC="${AE_QCACHE_SEC:-1.0}"

# ===== Check Python 3.11 =====
if ! command -v "$PY_BIN" >/dev/null 2>&1; then
  echo "[ERR] python3.11 not found. Install 3.11 and retry." >&2
  exit 1
fi

# ===== Create & activate venv =====
$PY_BIN -m venv .venv
source .venv/bin/activate
python -m pip install -U pip setuptools wheel

# ===== Install deps =====
if [[ -f requirements-dev.txt ]]; then
  pip install -r requirements-dev.txt || true
fi
if [[ -f requirements.txt ]]; then
  pip install -r requirements.txt || true
fi
# Install package in editable mode with all components; fall back to core if extras are missing
pip install -e ".[api,providers,ui]" || pip install -e .

# ===== Export runtime env =====
export DB_URL ASTROENGINE_HOME SE_EPHE_PATH
export AE_QCACHE_SIZE AE_QCACHE_SEC
mkdir -p "$ASTROENGINE_HOME"

# ===== Doctor / diagnostics (best-effort) =====
python - <<'PY'
try:
    import astroengine
    from importlib import metadata
    print("[OK] astroengine import:", astroengine.__name__)
    try:
        print("[INFO] version:", metadata.version("astroengine"))
    except Exception:
        pass
except Exception as e:
    print("[WARN] astroengine import failed:", e)
PY

# ===== Migrations (if Alembic present) =====
if command -v alembic >/dev/null 2>&1; then
  ALEMBIC_CONFIG=${ALEMBIC_CONFIG:-alembic.ini}
  echo "[INFO] Running alembic migrations..."
  alembic -c "$ALEMBIC_CONFIG" upgrade head || echo "[WARN] Alembic upgrade skipped/failed"
fi

# ===== Warm daily positions cache (best-effort) =====
python - <<PY
import os
bodies=os.getenv("AE_WARM_BODIES","sun,moon").split(",")
start=os.getenv("AE_WARM_START","2000-01-01")
end=os.getenv("AE_WARM_END","2030-12-31")
try:
    from astroengine.legacy.cache import warm as warm_cache
    warm_cache(bodies=bodies, start=start, end=end)
    print("[OK] Cache warmed for:", bodies)
except Exception as e:
    print("[WARN] Cache warm skipped:", e)
PY

# ===== Compile gate & quality gates =====
python -m compileall -q .
if command -v ruff >/dev/null 2>&1; then ruff check .; fi
if command -v black >/dev/null 2>&1; then black --check .; fi
if command -v isort >/dev/null 2>&1; then isort --check-only --profile black .; fi
if command -v mypy  >/dev/null 2>&1; then mypy || true; fi

# ===== Tests =====
if command -v pytest >/dev/null 2>&1; then pytest -q || true; fi

echo "\n[DONE] Bootstrap complete. Useful next commands:\n"
echo "  source .venv/bin/activate"
echo "  make run-api    # or: uvicorn $APP_MODULE --reload --port 8000"
echo "  make run-ui     # or: streamlit run $UI_ENTRY"
echo "  make run-cli    # see available CLI commands"
