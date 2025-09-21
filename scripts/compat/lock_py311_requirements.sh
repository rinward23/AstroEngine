# >>> AUTO-GEN BEGIN: lock py311 reqs v1.0
#!/usr/bin/env bash
set -euo pipefail
python -m pip install --upgrade pip pip-tools
mkdir -p requirements.lock
# If requirements.in exists, prefer it; otherwise fall back to requirements-dev.txt
if [[ -f requirements.in ]]; then
  pip-compile --resolver=backtracking --generate-hashes --output-file requirements.lock/py311.txt --extra dev \
    --unsafe-package pyswisseph --strip-extras requirements.in
else
  pip-compile --resolver=backtracking --generate-hashes --output-file requirements.lock/py311.txt requirements-dev.txt
fi
pipdeptree -w silence > requirements.lock/py311-deps.txt || true
# >>> AUTO-GEN END: lock py311 reqs v1.0
