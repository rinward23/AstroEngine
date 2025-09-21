# >>> AUTO-GEN BEGIN: AE CLI v1.3
from __future__ import annotations
import sys
import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .providers import get_provider, list_providers
from .engine import scan_contacts
from .exporters import SQLiteExporter, ParquetExporter
from .core.transit_engine import TransitEngine
from .validation import SchemaValidationError, available_schema_keys, validate_payload


def _parse_iso8601(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _body_code(name: str) -> int:
    try:
        import swisseph as swe
    except Exception as exc:  # pragma: no cover - dependency missing
        raise RuntimeError("pyswisseph is required for transit scans") from exc

    key = name.strip().upper()
    if not hasattr(swe, key):
        raise KeyError(f"Unknown body '{name}' for Swiss Ephemeris")
    return getattr(swe, key)


def cmd_env(args: argparse.Namespace) -> int:
    import importlib, os
    mods = ["pyswisseph", "numpy", "pandas"]
    missing = [m for m in mods if importlib.util.find_spec(m) is None]
    print("imports:", "ok" if not missing else f"missing={missing}")
    eph = os.environ.get("SE_EPHE_PATH") or os.environ.get("SWE_EPH_PATH")
    print("ephemeris:", eph or "(unset)")
    print("providers:", ", ".join(list_providers()) or "(none)")
    return 0


def cmd_provider(args: argparse.Namespace) -> int:
    if args.action == "list":
        print("available:", ", ".join(list_providers()) or "(none)")
        return 0
    prov = get_provider(args.name)
    out = prov.positions_ecliptic(args.iso, ["sun", "moon"])  # smoke
    print(out)
    return 0


def cmd_transits(args: argparse.Namespace) -> int:
    engine = TransitEngine.with_default_adapter()
    body = _body_code(args.body)
    start = _parse_iso8601(args.start)
    end = _parse_iso8601(args.end)
    events = list(
        engine.scan_longitude_crossing(
            body,
            float(args.target_longitude),
            float(args.aspect_angle),
            start,
            end,
            step_hours=float(args.step_hours),
        )
    )
    rows = []
    for event in events:
        data = asdict(event)
        if data.get("timestamp") is not None:
            data["timestamp"] = data["timestamp"].astimezone(timezone.utc).isoformat()
        rows.append(data)
    with open(args.json, "w", encoding="utf-8") as handle:
        json.dump(rows, handle, indent=2)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    if args.list:
        keys = available_schema_keys(args.kind)
        print("schemas:", ", ".join(keys) or "(none)")
        return 0
    if not args.schema or not args.payload:
        raise SystemExit("validate requires SCHEMA and PAYLOAD arguments unless --list is used")
    payload_path = Path(args.payload)
    payload = json.loads(payload_path.read_text())
    try:
        validate_payload(args.schema, payload)
    except SchemaValidationError as exc:
        print("validation failed:")
        for err in exc.errors:
            print(f" - {err}")
        return 1
    print("ok")
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    events = scan_contacts(
        start_iso=args.start,
        end_iso=args.end,
        moving=args.moving,
        target=args.target,
        provider_name=args.provider,
        decl_parallel_orb=args.decl_orb,
        decl_contra_orb=args.decl_orb,
        antiscia_orb=args.mirror_orb,
        contra_antiscia_orb=args.mirror_orb,
        step_minutes=args.step,
    )
    for e in events:
        print({
            "when": e.when_iso,
            "kind": e.kind,
            "pair": f"{e.moving}->{e.target}",
            "orb": round(e.orb_abs, 4),
            "phase": e.applying_or_separating,
            "score": round(e.score, 4),
        })
    if args.sqlite:
        SQLiteExporter(args.sqlite).write(events)
    if args.parquet:
        ParquetExporter(args.parquet).write(events)
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="astroengine", description="AstroEngine CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_env = sub.add_parser("env", help="Print environment diagnostics")
    p_env.set_defaults(fn=cmd_env)

    p_prov = sub.add_parser("provider", help="List/check providers")
    p_prov.add_argument("action", choices=["list", "check"], default="list")
    p_prov.add_argument("--name", default="swiss")
    p_prov.add_argument("--iso", default="2024-06-01T00:00:00Z")
    p_prov.set_defaults(fn=cmd_provider)

    p_trans = sub.add_parser("transits", help="Scan longitude crossings (JSON output)")
    p_trans.add_argument("--body", default="MARS", help="Swiss Ephemeris body name (e.g. MARS)")
    p_trans.add_argument("--target-longitude", required=True, help="Reference longitude degrees")
    p_trans.add_argument("--aspect-angle", default=0.0, help="Aspect angle to target in degrees")
    p_trans.add_argument("--start", required=True, help="ISO-8601Z start (UTC)")
    p_trans.add_argument("--end", required=True, help="ISO-8601Z end (UTC)")
    p_trans.add_argument("--step-hours", default=6.0, help="Step size in hours")
    p_trans.add_argument("--json", required=True, help="Write events to JSON path")
    p_trans.set_defaults(fn=cmd_transits)

    p_val = sub.add_parser("validate", help="Validate payloads against registered schemas")
    p_val.add_argument("schema", nargs="?")
    p_val.add_argument("payload", nargs="?")
    p_val.add_argument("--list", action="store_true", help="List available schema keys")
    p_val.add_argument("--kind", help="Optional schema kind filter")
    p_val.set_defaults(fn=cmd_validate)

    p_scan = sub.add_parser("scan", help="Scan window for declination/antiscia contacts (with scores)")
    p_scan.add_argument("--start", required=True, help="ISO-8601Z start (UTC)")
    p_scan.add_argument("--end", required=True, help="ISO-8601Z end (UTC)")
    p_scan.add_argument("--moving", default="mars")
    p_scan.add_argument("--target", default="venus")
    p_scan.add_argument("--provider", default="swiss", choices=["swiss", "skyfield"])
    p_scan.add_argument("--decl-orb", type=float, default=0.5)
    p_scan.add_argument("--mirror-orb", type=float, default=2.0)
    p_scan.add_argument("--step", type=int, default=60, help="minutes")
    p_scan.add_argument("--sqlite", help="write to SQLite path")
    p_scan.add_argument("--parquet", help="write to Parquet path")
    p_scan.set_defaults(fn=cmd_scan)

    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    ns = ap.parse_args(argv if argv is not None else sys.argv[1:])
    return int(ns.fn(ns))

if __name__ == "__main__":
    raise SystemExit(main())
# >>> AUTO-GEN END: AE CLI v1.3
