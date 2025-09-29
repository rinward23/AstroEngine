#!/usr/bin/env bash
set -euo pipefail

python -m qa.validation.cross_engine "$@"
