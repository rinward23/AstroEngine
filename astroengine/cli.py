# >>> AUTO-GEN BEGIN: AE CLI v1.1
"""AstroEngine command-line interface (minimal, stable entry)."""
from __future__ import annotations

import argparse
import sys


def _add_common_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--log-level", default="INFO", help="Log level: DEBUG, INFO, WARN, ERROR")


def cmd_env(args: argparse.Namespace) -> int:
    """Environment diagnostic: prints import and ephemeris status."""
    try:
        import importlib

        mods = ["pyswisseph", "numpy", "pandas"]
        missing = [m for m in mods if importlib.util.find_spec(m) is None]
        print("imports:", "ok" if not missing else f"missing={missing}")
    except Exception as e:  # pragma: no cover - diagnostic guard
        print("imports: error:", e)
    # Check ephemeris path hints (non-fatal)
    import os

    eph = os.environ.get("SE_EPHE_PATH") or os.environ.get("SWE_EPH_PATH")
    print("ephemeris:", eph or "(unset)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="astroengine", description="AstroEngine CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_env = sub.add_parser("env", help="Print environment diagnostics")
    _add_common_flags(p_env)
    p_env.set_defaults(fn=cmd_env)

    _register_core_commands(sub)
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    ns = parser.parse_args(argv)
    result = ns.fn(ns)
    return result if isinstance(result, int) else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
# >>> AUTO-GEN END: AE CLI v1.1

import json
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


def _cmd_transits(args: argparse.Namespace) -> list[TransitEvent]:
    engine = TransitEngine.with_default_adapter(EphemerisConfig())
    start = _parse_datetime(args.start)
    end = _parse_datetime(args.end)
    body: int | str = args.body
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


def _cmd_validate(args: argparse.Namespace) -> int:
    payload = json.loads(Path(args.path).read_text())
    validate_payload(args.schema, payload)
    print(f"Validation succeeded for schema {args.schema}")
    return 0


def _register_core_commands(subparsers) -> None:
    transits = subparsers.add_parser("transits", help="Scan for transiting aspects")
    transits.add_argument("--body", default="mars", help="Swiss Ephemeris body id or name (default: Mars)")
    transits.add_argument("--target-longitude", type=float, required=True)
    transits.add_argument("--aspect", type=float, default=0.0)
    transits.add_argument("--start", required=True, help="Start datetime (ISO-8601)")
    transits.add_argument("--end", required=True, help="End datetime (ISO-8601)")
    transits.add_argument("--step-hours", type=float, default=12.0)
    transits.add_argument("--json", help="Write events to JSON file")
    transits.set_defaults(fn=_cmd_transits)

    validate = subparsers.add_parser("validate", help="Validate JSON payloads against schemas")
    validate.add_argument("schema", help="Schema key registered in the data registry")
    validate.add_argument("path", help="Path to JSON file")
    validate.set_defaults(fn=_cmd_validate)
