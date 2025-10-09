# >>> AUTO-GEN BEGIN: lock py311 reqs v1.0
#!/usr/bin/env bash
set -euo pipefail
python -m pip install --upgrade pip pip-tools
mkdir -p requirements.lock
# Compile against the shared dev inputs (includes runtime via -r base.in)
python -m piptools compile --resolver=backtracking --generate-hashes \
  --output-file requirements.lock/py311.txt requirements/dev.in
python -m pipdeptree -w silence > requirements.lock/py311-deps.txt || true
# >>> AUTO-GEN END: lock py311 reqs v1.0
