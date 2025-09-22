#!/usr/bin/env bash
set -euo pipefail
mkdir -p scripts/githooks
chmod +x scripts/githooks/pre-commit
chmod +x scripts/githooks/pre-push

# Use repo-scoped hooks path so collaborators inherit hooks
git config core.hooksPath scripts/githooks
printf "Repo git hooks installed.\n"
