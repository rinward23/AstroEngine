# >>> AUTO-GEN BEGIN: repo cleanup v2.0
#!/usr/bin/env python
"""Repository housekeeping helpers.

The "light" mode mirrors the historical behaviour (remove ``__pycache__``
trees, ensure newlines at EOF, and opportunistically run ``ruff --fix``).
Deep mode expands the sweep to cover other ephemeral build artefacts and lets
contributors dry-run the process before deleting anything.  All actions are
confined to transient resources so the astrology module hierarchy remains
untouched.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

ROOT = Path(__file__).resolve().parents[2]

# Conservative default extensions considered "safe" for newline/trailing
# whitespace normalisation.  These cover our runtime code, docs, and config
# assets without touching binary datasets.  Dataset artefacts such as CSVs are
# intentionally excluded so the cleanup pass never mutates reference tables.
TEXT_EXTENSIONS = {
    ".cfg",
    ".ini",
    ".json",
    ".lock",
    ".md",
    ".py",
    ".rst",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}

# Directories that should never be normalised (vendor content, VCS metadata,
# or developer environments).
SKIP_TEXT_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "node_modules",
}

# High-sensitivity directory prefixes that should be left untouched by the
# normaliser because they contain curated astrology datasets or rule packs.
SKIP_TEXT_PREFIXES: tuple[tuple[str, ...], ...] = (
    ("datasets",),
    ("profiles",),
    ("rulesets",),
    ("astroengine", "data"),
)

# Patterns for directories/files we can safely purge across the repository.
LIGHT_PATTERNS = (
    "**/__pycache__",
    "**/*.pyc",
    "**/*.pyo",
)

DEEP_DIR_PATTERNS = (
    "**/.mypy_cache",
    "**/.nox",
    "**/.pytest_cache",
    "**/.ruff_cache",
    "**/.tox",
    "**/*.egg-info",
    "**/node_modules",
    "apps/**/.next",
    "apps/**/out",
    "build",
    "dist",
    "htmlcov",
    "pip-wheel-metadata",
    "site",
)

DEEP_FILE_PATTERNS = (
    "*.log",
    "*.tmp",
    ".coverage",
    "**/.coverage",
    ".coverage.*",
    "**/.coverage.*",
)


@dataclass
class CleanupSummary:
    """Tracks filesystem mutations performed during cleanup."""

    removed: list[Path] = field(default_factory=list)
    normalized: list[Path] = field(default_factory=list)

    def extend_removed(self, paths: Iterable[Path]) -> None:
        self.removed.extend(sorted(Path(p) for p in paths))

    def extend_normalized(self, paths: Iterable[Path]) -> None:
        self.normalized.extend(sorted(Path(p) for p in paths))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AstroEngine repository cleanup")
    parser.add_argument(
        "--deep",
        action="store_true",
        help="remove build artefacts, caches, and temporary files in addition to the light sweep",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print actions without mutating the filesystem",
    )
    parser.add_argument(
        "--skip-ruff",
        action="store_true",
        help="skip invoking ruff --fix even if it is available",
    )
    parser.add_argument(
        "--strip-trailing-whitespace",
        action="store_true",
        help="trim trailing whitespace for tracked text formats (implied by --deep)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="print every mutated path for easier auditing",
    )
    return parser.parse_args()


def iter_matches(patterns: Sequence[str]) -> Iterable[Path]:
    seen: set[Path] = set()
    for pattern in patterns:
        for path in ROOT.glob(pattern):
            try:
                rel = path.resolve().relative_to(ROOT)
            except ValueError:
                continue
            if rel in seen:
                continue
            seen.add(rel)
            yield ROOT / rel


def remove_paths(patterns: Sequence[str], *, dry_run: bool, verbose: bool) -> list[Path]:
    removed: list[Path] = []
    for path in iter_matches(patterns):
        if not path.exists():
            continue
        rel = path.relative_to(ROOT)
        removed.append(rel)
        if dry_run:
            print(f"[dry-run] remove {rel}")
            continue
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)
        if verbose:
            print(f"removed {rel}")
    return removed


def clean_text_files(*, strip_trailing: bool, dry_run: bool, verbose: bool) -> list[Path]:
    touched: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        rel = path.relative_to(ROOT)
        if any(part in SKIP_TEXT_DIR_NAMES for part in rel.parts):
            continue
        if any(rel.parts[: len(prefix)] == prefix for prefix in SKIP_TEXT_PREFIXES):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        normalised = text.replace("\r\n", "\n").replace("\r", "\n")
        if strip_trailing:
            lines = normalised.splitlines()
            normalised = "\n".join(line.rstrip() for line in lines)
            normalised += "\n"
        elif not normalised.endswith("\n"):
            normalised += "\n"
        if normalised == text:
            continue
        touched.append(rel)
        if dry_run:
            print(f"[dry-run] normalise {rel}")
            continue
        path.write_text(normalised, encoding="utf-8")
        if verbose:
            print(f"normalised {rel}")
    return touched


def run_ruff_fix(*, dry_run: bool, skip: bool) -> None:
    if skip:
        return
    cmd = [sys.executable, "-m", "ruff", "check", "--fix", str(ROOT)]
    if dry_run:
        print("[dry-run] would run:", " ".join(cmd))
        return
    try:
        subprocess.run(cmd, check=False)
    except FileNotFoundError:
        print("ruff not available; skipping lint fixes.")


def print_section(header: str, paths: Sequence[Path]) -> None:
    if not paths:
        return
    print(f"{header} ({len(paths)})")
    for rel in sorted(paths):
        print(f"  - {rel}")


def main() -> None:
    args = parse_args()
    summary = CleanupSummary()

    patterns = list(LIGHT_PATTERNS)
    strip_trailing = args.strip_trailing_whitespace or args.deep
    if args.deep:
        patterns.extend(DEEP_DIR_PATTERNS)
        patterns.extend(DEEP_FILE_PATTERNS)

    removed = remove_paths(patterns, dry_run=args.dry_run, verbose=args.verbose)
    summary.extend_removed(removed)

    normalized = clean_text_files(
        strip_trailing=strip_trailing,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )
    summary.extend_normalized(normalized)

    run_ruff_fix(dry_run=args.dry_run, skip=args.skip_ruff)

    print_section("Removed", summary.removed)
    print_section("Normalised", summary.normalized)

    print("Cleanup complete.")


if __name__ == "__main__":
    main()
# >>> AUTO-GEN END: repo cleanup v2.0
