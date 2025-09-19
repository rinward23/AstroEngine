# >>> AUTO-GEN BEGIN: AE Dev Setup (bash) v1.1
#!/usr/bin/env bash
set -euo pipefail
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .[dev]
python -m astroengine env || true
# >>> AUTO-GEN END: AE Dev Setup (bash) v1.1
