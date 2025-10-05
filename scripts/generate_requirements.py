#!/usr/bin/env python3
"""Generate requirement lock files from ``pyproject.toml`` definitions."""

from __future__ import annotations

import argparse
from collections import OrderedDict
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
REQ_MAIN = ROOT / "requirements.txt"
REQ_DEV = ROOT / "requirements-dev.txt"
REQ_OPTIONAL = ROOT / "requirements-optional.txt"

HEADER_MAIN = "# >>> AUTO-GEN BEGIN: AstroEngine Requirements v1.0"
FOOTER_MAIN = "# >>> AUTO-GEN END: AstroEngine Requirements v1.0"
HEADER_OPTIONAL = "# >>> AUTO-GEN BEGIN: optional-reqs v1.0"
FOOTER_OPTIONAL = "# >>> AUTO-GEN END: optional-reqs v1.0"

DEV_ENSURE_LINES = [
    "typing_extensions>=4.9.0  # ENSURE-LINE",
    "pip-tools>=7.4.0  # ENSURE-LINE",
    "pipdeptree>=2.20.0  # ENSURE-LINE",
    "pyswisseph==2.10.3.2; python_version <= \"3.11\"  # ENSURE-LINE",
]

DEV_EXTRA_OVERRIDES = {
    "pytest": "pytest>=8.0.0  # ENSURE-LINE",
    "hypothesis": "hypothesis>=6.92.0  # ENSURE-LINE",
    "pytest-benchmark": "pytest-benchmark>=4.0  # ENSURE-LINE",
    "pytest-cov": "pytest-cov>=4.1.0  # ENSURE-LINE",
    "ruff": "ruff>=0.6.5",
    "mypy": "mypy>=1.10",
}

ADDITIONAL_DEV_LINES = [
    "genbadge[coverage]>=1.1.1  # ENSURE-LINE",
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
    data = tomllib.loads(PYPROJECT.read_text())
    project = data.get("project", {})
    base = dedupe_preserve(list(project.get("dependencies", [])))
    extras_raw: dict[str, list[str]] = project.get("optional-dependencies", {})
    extras: dict[str, list[str]] = {}
    for name, values in extras_raw.items():
        extras[name] = dedupe_preserve(list(values))
    return base, extras


def format_with_header(header: str, body: list[str], footer: str) -> str:
    lines: list[str] = [header, "# Generated via scripts/generate_requirements.py; do not edit by hand."]
    lines.extend(body)
    if body and body[-1] != "":
        lines.append("")
    lines.append(footer)
    return "\n".join(lines) + "\n"


def generate_requirements_txt(base: list[str]) -> str:
    ordered = sorted(base, key=canonical_name)
    return format_with_header(HEADER_MAIN, ordered + [""], FOOTER_MAIN)


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


def generate_dev_txt(base: list[str], extras: dict[str, list[str]]) -> str:
    body: list[str] = []
    body.extend(DEV_ENSURE_LINES)
    body.append("")
    body.append("-r requirements.txt")
    body.append("")
    dev_extra = extras.get("dev", [])
    overrides = {canonical_name(k): v for k, v in DEV_EXTRA_OVERRIDES.items()}
    seen: set[str] = set()
    if dev_extra:
        body.append("# pyproject.toml [project.optional-dependencies.dev]")
        for spec in dev_extra:
            name = canonical_name(spec)
            seen.add(name)
            override = overrides.get(name)
            body.append(override or spec)
        body.append("")
    for name, override in overrides.items():
        if name not in seen:
            body.append(override)
    if ADDITIONAL_DEV_LINES:
        body.append("")
        body.extend(ADDITIONAL_DEV_LINES)
    return "\n".join(body).strip() + "\n"


def write_if_changed(path: Path, content: str) -> None:
    if path.exists() and path.read_text() == content:
        return
    path.write_text(content)


def main(check: bool = False) -> int:
    base, extras = load_pyproject()
    main_txt = generate_requirements_txt(base)
    optional_txt = generate_optional_txt(extras)
    dev_txt = generate_dev_txt(base, extras)

    if check:
        mismatches: list[str] = []
        if REQ_MAIN.read_text() != main_txt:
            mismatches.append("requirements.txt")
        if REQ_OPTIONAL.read_text() != optional_txt:
            mismatches.append("requirements-optional.txt")
        if REQ_DEV.read_text() != dev_txt:
            mismatches.append("requirements-dev.txt")
        if mismatches:
            print("Out-of-date files: " + ", ".join(mismatches))
            return 1
        return 0

    write_if_changed(REQ_MAIN, main_txt)
    write_if_changed(REQ_OPTIONAL, optional_txt)
    write_if_changed(REQ_DEV, dev_txt)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Only verify whether files are current.")
    args = parser.parse_args()
    raise SystemExit(main(check=args.check))
