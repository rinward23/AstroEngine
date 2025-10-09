#!/usr/bin/env python3
"""Generate requirement lock files from ``pyproject.toml`` definitions."""

from __future__ import annotations

import argparse
from collections import OrderedDict
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
REQ_BASE_IN = ROOT / "requirements" / "base.in"
REQ_DEV_IN = ROOT / "requirements" / "dev.in"
REQ_OPTIONAL = ROOT / "requirements-optional.txt"

HEADER_BASE = "# >>> AUTO-GEN BEGIN: AstroEngine base.in v2.0"
FOOTER_BASE = "# >>> AUTO-GEN END: AstroEngine base.in v2.0"
HEADER_DEV = "# >>> AUTO-GEN BEGIN: AstroEngine dev.in v2.0"
FOOTER_DEV = "# >>> AUTO-GEN END: AstroEngine dev.in v2.0"
HEADER_OPTIONAL = "# >>> AUTO-GEN BEGIN: optional-reqs v1.0"
FOOTER_OPTIONAL = "# >>> AUTO-GEN END: optional-reqs v1.0"

DEV_ENSURE_LINES = [
    "typing_extensions  # ENSURE-LINE",
    "pip-tools  # ENSURE-LINE",
    "pipdeptree  # ENSURE-LINE",
    "pyswisseph; python_version <= \"3.11\"  # ENSURE-LINE",
]

DEV_EXTRA_OVERRIDES = {
    "pytest": "pytest  # ENSURE-LINE",
    "hypothesis": "hypothesis  # ENSURE-LINE",
    "pytest-benchmark": "pytest-benchmark  # ENSURE-LINE",
    "pytest-cov": "pytest-cov  # ENSURE-LINE",
    "ruff": "ruff  # ENSURE-LINE",
    "mypy": "mypy  # ENSURE-LINE",
    "isort": "isort  # ENSURE-LINE",
    "black": "black  # ENSURE-LINE",
    "pre-commit": "pre-commit  # ENSURE-LINE",
    "mkdocs-material": "mkdocs-material  # ENSURE-LINE",
    "mkdocs-gen-files": "mkdocs-gen-files  # ENSURE-LINE",
}

ADDITIONAL_DEV_LINES = [
    "genbadge[coverage]  # ENSURE-LINE",
    "psycopg[binary]",
    "testcontainers[postgres]",
]

OPTIONAL_SKIP_EXTRAS = {"all", "dev"}


def canonical_name(spec: str) -> str:
    spec = spec.split(";", 1)[0]
    spec = spec.split("[", 1)[0]
    for token in ("==", "!=", ">=", "<=", "~=", ">", "<"):
        if token in spec:
            spec = spec.split(token, 1)[0]
            break
    return spec.strip().lower().replace("-", "_")


def unpin(spec: str) -> str:
    raw = spec.rstrip()
    if not raw or raw.startswith("#"):
        return raw
    comment = ""
    if "#" in raw:
        raw, comment = raw.split("#", 1)
        comment = "#" + comment.strip()
    marker = ""
    if ";" in raw:
        raw, marker = raw.split(";", 1)
        marker = "; " + marker.strip()
    tokens = ["==", "!=", ">=", "<=", "~=", ">", "<"]
    cut = len(raw)
    for token in tokens:
        idx = raw.find(token)
        if idx != -1 and idx < cut:
            cut = idx
    raw = raw[:cut].strip()
    line = raw
    if marker:
        line = f"{line} {marker}" if line else marker
    if comment:
        line = f"{line}  {comment}" if line else comment
    return line.strip()


def dedupe_preserve(items: list[str]) -> list[str]:
    seen: OrderedDict[str, str] = OrderedDict()
    for raw in items:
        item = raw.strip()
        if not item or item.startswith("#"):
            continue
        key = (item.split(" ", 1)[0], canonical_name(item))
        if key not in seen:
            seen[key] = item
    return list(seen.values())


def load_pyproject() -> tuple[list[str], dict[str, list[str]]]:
    raw_lines = PYPROJECT.read_text().splitlines()
    extras_aliases: dict[str, str] = {}
    extras_seen: set[str] = set()
    sanitized: list[str] = []
    in_optional = False
    for line in raw_lines:
        stripped = line.strip()
        if stripped == "[project.optional-dependencies]":
            in_optional = True
            sanitized.append(line)
            continue
        if in_optional and stripped.startswith("[") and stripped.endswith("]"):
            in_optional = False
        if in_optional and "=" in line and stripped.endswith("["):
            key = line.split("=", 1)[0].strip()
            alias = key
            if alias in extras_seen:
                suffix = 1
                candidate = f"{alias}__dup{suffix}"
                while candidate in extras_seen:
                    suffix += 1
                    candidate = f"{alias}__dup{suffix}"
                line = line.replace(key, candidate, 1)
                extras_aliases[candidate] = alias
                extras_seen.add(candidate)
            else:
                extras_aliases[alias] = alias
                extras_seen.add(alias)
        sanitized.append(line)
    data = tomllib.loads("\n".join(sanitized))
    project = data.get("project", {})
    base = dedupe_preserve(list(project.get("dependencies", [])))
    extras_raw: dict[str, list[str]] = project.get("optional-dependencies", {})
    extras: dict[str, list[str]] = {}
    for name, values in extras_raw.items():
        canonical = extras_aliases.get(name, name)
        if canonical in extras:
            continue
        extras[canonical] = dedupe_preserve(list(values))
    return base, extras


def format_with_header(header: str, body: list[str], footer: str) -> str:
    lines: list[str] = [header, "# Generated via scripts/generate_requirements.py; do not edit by hand."]
    lines.extend(body)
    if body and body[-1] != "":
        lines.append("")
    lines.append(footer)
    return "\n".join(lines) + "\n"


def generate_base_in(base: list[str]) -> str:
    unpinned = [unpin(spec) for spec in base]
    ordered = sorted(dedupe_preserve(unpinned), key=canonical_name)
    body = ["# Core runtime dependencies (unpinned)", ""]
    body.extend(ordered)
    return format_with_header(HEADER_BASE, body, FOOTER_BASE)


def generate_optional_txt(extras: dict[str, list[str]]) -> str:
    body: list[str] = ["# Mirrors pyproject extras for non-pep517 workflows", ""]
    for name, pkgs in extras.items():
        if name in OPTIONAL_SKIP_EXTRAS:
            continue
        body.append(f"# [{name}]")
        body.extend(pkgs)
        body.append("")
    if body and body[-1] == "":
        body.pop()
    return format_with_header(HEADER_OPTIONAL, body, FOOTER_OPTIONAL)


def generate_dev_in(base: list[str], extras: dict[str, list[str]]) -> str:
    body: list[str] = ["-r base.in", ""]
    body.extend(DEV_ENSURE_LINES)
    body.append("")
    dev_extra = [unpin(spec) for spec in extras.get("dev", [])]
    overrides = {canonical_name(k): v for k, v in DEV_EXTRA_OVERRIDES.items()}
    seen: set[str] = set()
    if dev_extra:
        body.append("# pyproject.toml [project.optional-dependencies.dev]")
        for spec in dev_extra:
            name = canonical_name(spec)
            seen.add(name)
            body.append(spec)
        body.append("")
    for name, override in overrides.items():
        if name not in seen:
            body.append(override)
    if ADDITIONAL_DEV_LINES:
        body.append("")
        body.extend(ADDITIONAL_DEV_LINES)
    return format_with_header(HEADER_DEV, body, FOOTER_DEV)


def write_if_changed(path: Path, content: str) -> None:
    if path.exists() and path.read_text() == content:
        return
    path.write_text(content)


def main(check: bool = False) -> int:
    base, extras = load_pyproject()
    base_in = generate_base_in(base)
    optional_txt = generate_optional_txt(extras)
    dev_in = generate_dev_in(base, extras)

    if check:
        mismatches: list[str] = []
        if REQ_BASE_IN.read_text() != base_in:
            mismatches.append("requirements/base.in")
        if REQ_OPTIONAL.read_text() != optional_txt:
            mismatches.append("requirements-optional.txt")
        if REQ_DEV_IN.read_text() != dev_in:
            mismatches.append("requirements/dev.in")
        if mismatches:
            print("Out-of-date files: " + ", ".join(mismatches))
            return 1
        return 0

    REQ_BASE_IN.parent.mkdir(parents=True, exist_ok=True)
    write_if_changed(REQ_BASE_IN, base_in)
    write_if_changed(REQ_OPTIONAL, optional_txt)
    write_if_changed(REQ_DEV_IN, dev_in)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Only verify whether files are current.")
    args = parser.parse_args()
    raise SystemExit(main(check=args.check))
