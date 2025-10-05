"""Dataset export helpers for the modular CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

from ..exporters_batch import export_parquet_dataset


def _load_events(path: str, fmt: str, key: str | None) -> list[dict]:
    if path == "-":
        payload_text = sys.stdin.read()
    else:
        payload_text = Path(path).read_text(encoding="utf-8")

    if fmt == "jsonl":
        return [json.loads(line) for line in payload_text.splitlines() if line.strip()]

    document = json.loads(payload_text)
    if isinstance(document, list):
        return document
    if isinstance(document, dict):
        lookup = key or "events"
        if lookup not in document:
            raise KeyError(lookup)
        value = document[lookup]
        if isinstance(value, list):
            return value
    raise TypeError("unsupported JSON payload structure")


def add_subparser(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the ``export`` subcommand."""

    parser = sub.add_parser(
        "export",
        help="Export canonical event datasets",
        description=(
            "Convert JSON or JSONL payloads into canonical AstroEngine datasets. "
            "Supports stdin ('-') for streaming input."
        ),
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Input JSON/JSONL file (use '-' for stdin)",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Destination path for the exported dataset",
    )
    parser.add_argument(
        "--format",
        choices=("json", "jsonl"),
        default="jsonl",
        help="Input format (default: jsonl)",
    )
    parser.add_argument(
        "--key",
        help="JSON key containing events when --format json (default: events)",
    )
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    """Execute the export subcommand."""

    try:
        events: Iterable[dict] = _load_events(args.input, args.format, args.key)
    except Exception as exc:  # pragma: no cover - surface for CLI usage
        print(f"failed to load input events: {exc}", file=sys.stderr)
        return 1

    try:
        written = export_parquet_dataset(args.out, events)
    except Exception as exc:  # pragma: no cover - dataset I/O issues are reported
        print(f"export failed: {exc}", file=sys.stderr)
        return 1

    print(f"wrote {written} events to {args.out}")
    return 0
