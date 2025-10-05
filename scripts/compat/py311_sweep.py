# >>> AUTO-GEN BEGIN: py311 compatibility sweep v1.0
"""
Scan the repo for patterns that require Python newer than 3.11 and make **safe**
3.11 fallbacks:
- Replace `from typing import override` -> `from typing_extensions import override`.
- Replace `typing.override` -> `typing_extensions.override`.
- Detect PEP-695 generic syntax (functions/classes like `def f[T](...)`) and **report** occurrences.
- Write a Markdown report to `.github/compat/py311_sweep_report.md`.
- Exit with code 0 (non-blocking); the workflow will create a PR if fixes occurred.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = Path(__file__).resolve()
REPORT = ROOT / ".github/compat/py311_sweep_report.md"

# patterns
IMPORT_OVERRIDE = re.compile(r"^\s*from\s+typing\s+import\s+override\s*$")
ATTR_OVERRIDE = re.compile(r"(?<!\w)typing\.override(?!\w)")
PEP695_DEF = re.compile(r"^\s*def\s+\w+\[[^\]]+\]\s*\(")
PEP695_CLASS = re.compile(r"^\s*class\s+\w+\[[^\]]+\]\s*[:(]")

changes = []
pep695_hits = []

# candidate files
files = [
    p for p in ROOT.rglob("*.py") if "/.venv/" not in str(p) and "/.git/" not in str(p)
]
for p in files:
    if p == SCRIPT:
        continue
    try:
        src = p.read_text(encoding="utf-8")
    except Exception:
        continue

    original = src
    lines = src.splitlines()
    new_lines = []
    for line in lines:
        # fix: from typing import override
        if IMPORT_OVERRIDE.match(line):
            line = "from typing_extensions import override"
        # fix: typing.override -> typing_extensions.override
        line = ATTR_OVERRIDE.sub("typing_extensions.override", line)
        new_lines.append(line)

    # detect PEP-695 syntax (report-only)
    for i, line in enumerate(lines, 1):
        if PEP695_DEF.search(line) or PEP695_CLASS.search(line):
            pep695_hits.append(f"{p.relative_to(ROOT)}:{i}: {line.strip()[:120]}")

    new_src = "\n".join(new_lines)
    if src.endswith("\n") and not new_src.endswith("\n"):
        new_src += "\n"
    if new_src != original:
        p.write_text(new_src, encoding="utf-8")
        changes.append(str(p.relative_to(ROOT)))

# write report
out = []
out.append("# Python 3.11 Compatibility Sweep Report\n")
if changes:
    out.append("## Applied safe fixes\n")
    for c in changes:
        out.append(f"- replaced override usage in `{c}`")
else:
    out.append("## No safe fixes were needed\n")

if pep695_hits:
    out.append("\n## PEP-695 generic syntax detected (manual review)\n")
    for h in pep695_hits[:200]:
        out.append(f"- {h}")
else:
    out.append("\n## No PEP-695 syntax found\n")

REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text("\n".join(out), encoding="utf-8")
print(REPORT)
# >>> AUTO-GEN END: py311 compatibility sweep v1.0
