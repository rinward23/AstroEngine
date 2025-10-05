"""Dataset export helpers for the modular CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, Tuple

from astroengine.config import load_settings
from astroengine.visual import (
    MultiWheelComposition,
    MultiWheelLayer,
    MultiWheelOptions,
    export_multiwheel,
)

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
        help="Input JSON/JSONL file (use '-' for stdin)",
    )
    parser.add_argument(
        "--out",
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
    parser.add_argument(
        "--multiwheel-spec",
        help="JSON file describing a multi-wheel composition to export",
    )
    parser.add_argument(
        "--multiwheel-out",
        help="Destination file for rendered multi-wheel output (requires --multiwheel-spec)",
    )
    parser.add_argument(
        "--multiwheel-format",
        choices=("svg", "png"),
        default="svg",
        help="Output format for multi-wheel export (default: svg)",
    )
    parser.set_defaults(func=run)


def _parse_multiwheel_spec(path: str) -> Tuple[MultiWheelComposition, MultiWheelOptions]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if "layers" not in data or not isinstance(data["layers"], list):
        raise ValueError("multi-wheel spec must include a 'layers' list")
    layers: list[MultiWheelLayer] = []
    for entry in data["layers"]:
        if not isinstance(entry, dict):
            raise TypeError("layer entries must be objects")
        bodies = entry.get("bodies")
        if not isinstance(bodies, dict) or not bodies:
            raise ValueError("each layer requires a non-empty 'bodies' mapping")
        houses = entry.get("houses")
        declinations = entry.get("declinations")
        layer = MultiWheelLayer(
            label=str(entry.get("label", f"Layer {len(layers) + 1}")),
            bodies={str(name): float(lon) for name, lon in bodies.items()},
            houses=[float(x) for x in houses] if isinstance(houses, (list, tuple)) else None,
            declinations={str(name): float(dec) for name, dec in (declinations or {}).items()},
        )
        layers.append(layer)
    composition = MultiWheelComposition(
        layers=tuple(layers),
        title=data.get("title"),
        subtitle=data.get("subtitle"),
    )
    options_data = data.get("options") or {}
    options = MultiWheelOptions(**options_data)
    return composition, options


def _run_multiwheel_export(args: argparse.Namespace) -> int:
    if not args.multiwheel_out:
        print("--multiwheel-out is required when --multiwheel-spec is provided", file=sys.stderr)
        return 2
    try:
        composition, options = _parse_multiwheel_spec(args.multiwheel_spec)
    except Exception as exc:  # pragma: no cover - reported to user
        print(f"failed to parse multi-wheel spec: {exc}", file=sys.stderr)
        return 1
    settings = load_settings()
    try:
        payload = export_multiwheel(
            composition,
            options=options,
            settings=settings,
            fmt=args.multiwheel_format,
        )
    except Exception as exc:  # pragma: no cover - render issues surfaced to user
        print(f"render failed: {exc}", file=sys.stderr)
        return 1
    Path(args.multiwheel_out).write_bytes(payload)
    wheel_count = len(composition.layers)
    print(f"rendered {wheel_count}-wheel composition to {args.multiwheel_out}")
    return 0


def run(args: argparse.Namespace) -> int:
    """Execute the export subcommand."""

    if args.multiwheel_spec:
        return _run_multiwheel_export(args)

    if not args.input or not args.out:
        print("--input and --out are required for dataset export", file=sys.stderr)
        return 2

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
