"""Command line interface for AstroEngine."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from .core import TransitEngine, TransitEvent
from .ephemeris import EphemerisConfig
from .validation import validate_payload

BODY_IDS = {
    "sun": 0,
    "moon": 1,
    "mercury": 2,
    "venus": 3,
    "mars": 4,
    "jupiter": 5,
    "saturn": 6,
    "uranus": 7,
    "neptune": 8,
    "pluto": 9,
}


def _parse_datetime(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def _command_transits(args: argparse.Namespace) -> list[TransitEvent]:
    engine = TransitEngine.with_default_adapter(EphemerisConfig())
    start = _parse_datetime(args.start)
    end = _parse_datetime(args.end)
    body = args.body
    if isinstance(body, str):
        key = body.lower()
        if key in BODY_IDS:
            body = BODY_IDS[key]
        else:
            try:
                body = int(key)
            except ValueError as exc:  # pragma: no cover - defensive guard
                raise SystemExit(f"Unknown body identifier: {args.body}") from exc

    events = list(
        engine.scan_longitude_crossing(
            body,
            args.target_longitude,
            args.aspect,
            start,
            end,
            step_hours=args.step_hours,
        )
    )
    if args.json:
        Path(args.json).write_text(json.dumps([asdict(e) for e in events], default=str, indent=2))
    else:
        for event in events:
            timestamp = event.timestamp.isoformat() if event.timestamp else "unknown"
            print(f"{timestamp} | orb={event.orb:.6f}° | motion={event.motion}")
    return events


def _command_validate(args: argparse.Namespace) -> None:
    payload = json.loads(Path(args.path).read_text())
    validate_payload(args.schema, payload)
    print(f"Validation succeeded for schema {args.schema}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="astroengine", description="AstroEngine CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    transits = subparsers.add_parser("transits", help="Scan for transiting aspects")
    transits.add_argument(
        "--body", default="mars", help="Swiss Ephemeris body id or name (default: Mars)"
    )
    transits.add_argument("--target-longitude", type=float, required=True)
    transits.add_argument("--aspect", type=float, default=0.0)
    transits.add_argument("--start", required=True, help="Start datetime (ISO-8601)")
    transits.add_argument("--end", required=True, help="End datetime (ISO-8601)")
    transits.add_argument("--step-hours", type=float, default=12.0)
    transits.add_argument("--json", help="Write events to JSON file")
    transits.set_defaults(func=_command_transits)

    validate = subparsers.add_parser("validate", help="Validate JSON payloads against schemas")
    validate.add_argument("schema", help="Schema key registered in the data registry")
    validate.add_argument("path", help="Path to JSON file")
    validate.set_defaults(func=_command_validate)

    return parser


def main(argv: Sequence[str] | None = None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    main()
