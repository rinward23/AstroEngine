#!/usr/bin/env python3
"""Utilities for consolidating historical astrology rulesets."""

from __future__ import annotations

import argparse
import csv
import datetime
import json
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - guidance for manual invocations
    print("Please `pip install pyyaml` and rerun.", file=sys.stderr)
    sys.exit(1)

REQUIRED_MODULE_IDS = {"aspects", "transits", "scoring", "narrative"}
TS_FMT_FILE = "%Y%m%d-%H%M"  # for filenames


ModuleRegistry = dict[str, list[dict[str, Any]]]
ParsingErrors = list[tuple[str, str]]


def iso_to_dt(value: str | None) -> datetime.datetime | None:
    """Parse a loose ISO 8601 timestamp to a datetime."""

    if not value:
        return None

    cleaned = value.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1]

    formats = ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d")
    for fmt in formats:
        try:
            return datetime.datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    return None


def load_any(path: Path) -> tuple[Any | None, str | None]:
    """Load YAML or JSON data from *path* and return (data, error)."""

    text = path.read_text(encoding="utf-8")
    try:
        suffix = path.suffix.lower()
        if suffix in {".yaml", ".yml"}:
            data = yaml.safe_load(text)
        elif suffix == ".json":
            data = json.loads(text)
        else:
            return None, "Unsupported extension"
    except Exception as exc:  # pragma: no cover - defensive guardrails
        return None, f"Parse error: {exc}"
    return data, None


def extract_header(document: Any, source: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Extract standard metadata from a ruleset document."""

    if not isinstance(document, dict):
        return None, "Top-level must be a mapping"

    header = {
        "id": document.get("id"),
        "name": document.get("name"),
        "version": document.get("version"),
        "status": document.get("status", "active"),
        "supersedes": document.get("supersedes"),
        "source_file": str(source),
    }

    errors: list[str] = []
    if not header["id"]:
        errors.append("Missing 'id'")
    if not header["version"]:
        errors.append("Missing 'version'")

    version_dt = iso_to_dt(header["version"])
    if not version_dt:
        errors.append("Bad 'version' (expect ISO like 2025-09-03T22:41Z)")
    header["_version_dt"] = version_dt

    if errors:
        return None, ", ".join(errors)
    return header, None


def ensure_dirs(paths: Iterable[Path]) -> None:
    for directory in paths:
        directory.mkdir(parents=True, exist_ok=True)


def discover_source_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.suffix.lower() in {".yaml", ".yml", ".json"}
    )


def build_registry(files: Iterable[Path]) -> tuple[ModuleRegistry, ParsingErrors]:
    registry: ModuleRegistry = {}
    parsing_errors: ParsingErrors = []

    for path in files:
        data, parse_error = load_any(path)
        if parse_error:
            parsing_errors.append((str(path), parse_error))
            continue

        header, header_error = extract_header(data, path)
        if header_error:
            parsing_errors.append((str(path), header_error))
            continue

        entry = {
            "id": header["id"],
            "name": header["name"],
            "version": header["version"],
            "status": header["status"],
            "supersedes": header["supersedes"],
            "_version_dt": header["_version_dt"],
            "source_file": header["source_file"],
            "body": data,
        }
        registry.setdefault(header["id"], []).append(entry)

    return registry, parsing_errors


def compute_lineage(registry: ModuleRegistry) -> tuple[dict[str, dict[str, Any]], ModuleRegistry]:
    latest_by_id: dict[str, dict[str, Any]] = {}
    lineage_by_id: ModuleRegistry = {}

    for module_id, entries in registry.items():
        valid_entries = [entry for entry in entries if entry["_version_dt"] is not None]
        valid_entries.sort(key=lambda entry: entry["_version_dt"])
        if not valid_entries:
            continue
        latest_by_id[module_id] = valid_entries[-1]
        lineage_by_id[module_id] = valid_entries

    return latest_by_id, lineage_by_id


def write_manifest(manifest_path: Path, lineage_by_id: ModuleRegistry, latest_by_id: dict[str, dict[str, Any]]) -> None:
    header = [
        "module_id",
        "name",
        "version",
        "status",
        "supersedes",
        "source_file",
        "is_latest",
    ]

    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for module_id, entries in lineage_by_id.items():
            for entry in entries:
                writer.writerow(
                    [
                        entry["id"],
                        entry["name"],
                        entry["version"],
                        entry["status"],
                        entry["supersedes"],
                        entry["source_file"],
                        "yes" if entry is latest_by_id[module_id] else "no",
                    ]
                )


def write_validation_report(
    report_path: Path,
    parsing_errors: ParsingErrors,
    missing_required: list[str],
    registry: ModuleRegistry,
    latest_by_id: dict[str, dict[str, Any]],
) -> None:
    with report_path.open("w", encoding="utf-8") as handle:
        handle.write("# Validation Report\n\n")

        if parsing_errors:
            handle.write("## Parsing / Header Errors\n")
            for path, error in parsing_errors:
                handle.write(f"- {path}: {error}\n")
            handle.write("\n")

        if missing_required:
            handle.write("## Missing Required Modules\n")
            for module_id in missing_required:
                handle.write(f"- {module_id}\n")
            handle.write("\n")
        else:
            handle.write("All required modules present: aspects, transits, scoring, narrative.\n\n")

        handle.write("## Module Counts\n")
        handle.write(f"- Unique module ids found: {len(registry)}\n")
        handle.write(f"- Latest modules selected: {len(latest_by_id)}\n")


def emit_latest_modules(overrides_dir: Path, latest_by_id: dict[str, dict[str, Any]], ts_file: str) -> list[str]:
    emitted: list[str] = []

    for module_id, entry in sorted(latest_by_id.items()):
        body = entry["body"]
        body["id"] = entry["id"]
        if entry["name"] is not None:
            body["name"] = entry["name"]
        body["version"] = entry["version"]
        body["status"] = entry["status"]
        if entry["supersedes"] is not None:
            body["supersedes"] = entry["supersedes"]

        target = overrides_dir / f"{module_id}__v{ts_file}.yaml"
        with target.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(body, handle, sort_keys=False, allow_unicode=True)
        emitted.append(str(target))

    return emitted


def emit_combined_ruleset(destination: Path, latest_by_id: dict[str, dict[str, Any]]) -> None:
    stitched = {"modules": {}}
    for module_id, entry in latest_by_id.items():
        stitched["modules"][module_id] = entry["body"]

    with destination.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(stitched, handle, sort_keys=False, allow_unicode=True)


def write_changelog(
    changelog_path: Path,
    generated_at: datetime.datetime,
    overrides_dir: Path,
    lineage_by_id: ModuleRegistry,
    latest_by_id: dict[str, dict[str, Any]],
) -> None:
    with changelog_path.open("w", encoding="utf-8") as handle:
        handle.write("# Ruleset Change Log (Consolidation)\n\n")
        handle.write(f"- Consolidation time (UTC): {generated_at.isoformat(timespec='seconds')}Z\n")
        handle.write(f"- Output (overrides): {overrides_dir}\n\n")

        for module_id, entries in sorted(lineage_by_id.items()):
            handle.write(f"## {module_id}\n")
            for entry in entries:
                suffix = " (latest)" if entry is latest_by_id[module_id] else ""
                name = entry.get("name") or ""
                handle.write(f"- {entry['version']} — {name} [{entry['status']}]{suffix}\n")
            handle.write("\n")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild consolidated astrology ruleset from all iterations (append-only)."
    )
    parser.add_argument(
        "--in",
        dest="in_dir",
        required=True,
        help="Folder containing ALL past iterations (yaml/json)",
    )
    parser.add_argument(
        "--out",
        dest="out_dir",
        default="./rulesets",
        help="Output folder (default ./rulesets)",
    )
    parser.add_argument(
        "--single",
        dest="emit_single",
        action="store_true",
        help="Emit combined ruleset.main.yaml",
    )
    return parser.parse_args(argv)


def run(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    in_dir = Path(args.in_dir)
    out_root = Path(args.out_dir)
    base_dir = out_root / "base"
    overrides_dir = out_root / "overrides"
    report_dir = out_root / "_reports"

    ensure_dirs((base_dir, overrides_dir, report_dir))

    source_files = discover_source_files(in_dir)
    if not source_files:
        print("No YAML/JSON files found in input directory.", file=sys.stderr)
        return 2

    registry, parsing_errors = build_registry(source_files)
    latest_by_id, lineage_by_id = compute_lineage(registry)
    missing_required = sorted(module for module in REQUIRED_MODULE_IDS if module not in latest_by_id)

    generated_at = datetime.datetime.utcnow()
    timestamp = generated_at.strftime(TS_FMT_FILE)

    manifest_path = report_dir / f"RULESET__MANIFEST_{timestamp}.csv"
    write_manifest(manifest_path, lineage_by_id, latest_by_id)

    validation_path = report_dir / f"RULESET__VALIDATION_{timestamp}.md"
    write_validation_report(validation_path, parsing_errors, missing_required, registry, latest_by_id)

    if missing_required:
        print(f"Missing required modules: {', '.join(missing_required)}", file=sys.stderr)
        print(f"See validation: {validation_path}", file=sys.stderr)
        return 3

    emit_latest_modules(overrides_dir, latest_by_id, timestamp)

    stitched_path: Path | None = None
    if args.emit_single:
        stitched_path = out_root / "ruleset.main.yaml"
        emit_combined_ruleset(stitched_path, latest_by_id)

    changelog_path = report_dir / f"RULESET__CHANGELOG_{timestamp}.md"
    write_changelog(changelog_path, generated_at, overrides_dir, lineage_by_id, latest_by_id)

    print("Consolidation complete.")
    print(f"- Manifest: {manifest_path}")
    print(f"- Validation: {validation_path}")
    print(f"- Changelog: {changelog_path}")
    if stitched_path is not None:
        print(f"- Stitched: {stitched_path}")
    print(f"- Latest modules written to: {overrides_dir}")

    return 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
