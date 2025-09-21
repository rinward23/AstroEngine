# >>> AUTO-GEN BEGIN: validate registry v1.0
from __future__ import annotations
from pathlib import Path
import sys, yaml
REG = Path("registry")
REQ = ["aspects.yaml", "orbs_policy.yaml", "domains.yaml", "plugins.yaml"]
missing = [f for f in REQ if not (REG / f).exists()]
if missing:
    print("Missing registry files:", ", ".join(missing)); sys.exit(2)
ids = []
for fname in ["aspects.yaml"]:
    data = yaml.safe_load((REG / fname).read_text()) or {}
    for row in data.get("aspects", []):
        ids.append(row.get("id"))
for fname in ["plugins.yaml"]:
    data = yaml.safe_load((REG / fname).read_text()) or {}
    for row in data.get("plugins", []):
        ids.append(row.get("id"))
dups = {i for i in ids if ids.count(i) > 1}
if dups:
    print("Duplicate IDs:", ", ".join(sorted(dups))); sys.exit(2)
# >>> AUTO-GEN END: validate registry v1.0
