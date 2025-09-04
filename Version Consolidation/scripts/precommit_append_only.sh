#!/usr/bin/env bash
# Blocks in-place edits to rulesets/overrides/* unless file name includes __vYYYYMMDD-HHMM.yaml
set -euo pipefail

pattern='__v[0-9]{8}-[0-9]{4}\.yaml$'

changed=$(git diff --cached --name-status || true)

# Allow commits with no changes
[ -z "$changed" ] && exit 0

fail=0
while IFS=$'\t' read -r status file; do
  # Only consider overrides path
  if [[ "$file" == rulesets/overrides/* ]]; then
    # Newly added files are OK if they match the versioned pattern
    if [[ "$status" == A* ]]; then
      if [[ ! "$file" =~ $pattern ]]; then
        echo "ERROR: New overrides file does not follow append-only pattern: $file" >&2
        fail=1
      fi
    else
      # Any modification to existing overrides file is blocked
      echo "ERROR: In-place modification detected in overrides: $file" >&2
      echo "       Use a NEW file with a timestamped suffix (__vYYYYMMDD-HHMM.yaml)." >&2
      fail=1
    fi
  fi
done <<< "$changed"

if [[ $fail -ne 0 ]]; then
  echo "Pre-commit hook failed."
  exit 1
fi

exit 0
