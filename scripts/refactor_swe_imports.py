"""Codemod to replace direct swisseph imports with the lazy swe() accessor."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INCLUDE_DIRS = ["astroengine", "app", "ui", "core", "scripts", "tests", "generated"]
EXCLUDE_DIRS = {".git", ".venv", "venv", "__pycache__", "migrations", "dist", "build"}

PATTERNS = [
    (
        re.compile(r"^\s*import\s+swisseph\s+as\s+swe\s*(?:#.*)?$", re.M),
        "from astroengine.ephemeris.swe import swe",
    ),
    (
        re.compile(r"^\s*import\s+swisseph\s*$", re.M),
        "from astroengine.ephemeris.swe import swe",
    ),
]
CALLS = [
    (re.compile(r"\bswe\.calc_ut\s*\("), "swe().calc_ut("),
    (re.compile(r"\bswe\.julday\s*\("), "swe().julday("),
    (re.compile(r"\bswe\.set_ephe_path\s*\("), "swe().set_ephe_path("),
]
ATTRS = re.compile(r"\bswe\.([A-Za-z_][A-Za-z0-9_]*)")


def should_process(path: Path) -> bool:
    if path.suffix != ".py":
        return False
    if any(part in EXCLUDE_DIRS for part in path.parts):
        return False
    return any(str(path).startswith(str(ROOT / inc)) for inc in INCLUDE_DIRS)


def _replace_attr(match: re.Match[str]) -> str:
    name = match.group(1)
    return f"swe().{name}"


def patch_text(text: str) -> tuple[str, int]:
    count = 0
    for pattern, repl in PATTERNS:
        text, n = pattern.subn(repl, text)
        count += n
    for pattern, repl in CALLS:
        text, n = pattern.subn(repl, text)
        count += n
    text, n = ATTRS.subn(_replace_attr, text)
    count += n
    return text, count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write changes to disk")
    args = parser.parse_args()

    total = 0
    for path in ROOT.rglob("*.py"):
        if not should_process(path):
            continue
        original = path.read_text(encoding="utf-8")
        patched, count = patch_text(original)
        if count:
            total += count
            print(f"[{count:3d}] {path.relative_to(ROOT)}")
            if args.apply:
                path.write_text(patched, encoding="utf-8")
    mode = "APPLIED" if args.apply else "DRY RUN"
    print(f"Total replacements: {total}. {mode}")


if __name__ == "__main__":
    main()
