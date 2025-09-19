# >>> AUTO-GEN BEGIN: AE CLI v1.2
"""AstroEngine command-line interface with provider, star, and decl utilities."""
from __future__ import annotations

import argparse
import sys
import datetime as _dt

from .providers import get_provider, list_providers


def _add_common_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--log-level", default="INFO", help="Log level: DEBUG, INFO, WARN, ERROR")


def cmd_env(args: argparse.Namespace) -> int:
    import importlib
    mods = ["pyswisseph", "numpy", "pandas"]
    missing = [m for m in mods if importlib.util.find_spec(m) is None]
    print("imports:", "ok" if not missing else f"missing={missing}")
    import os
    eph = os.environ.get("SE_EPHE_PATH") or os.environ.get("SWE_EPH_PATH")
    print("ephemeris:", eph or "(unset)")
    print("providers:", ", ".join(list_providers()) or "(none)")
    return 0


def cmd_providers(args: argparse.Namespace) -> int:
    if args.action == "list":
        print("available:", ", ".join(list_providers()) or "(none)")
        return 0
    if args.action == "check":
        prov = get_provider(args.name)
        now = _dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
        out = prov.positions_ecliptic(now, ["sun", "moon"])  # smoke
        print(out)
        return 0
    return 1


def cmd_star(args: argparse.Namespace) -> int:
    iso = args.iso or (_dt.datetime.utcnow().isoformat(timespec="seconds") + "Z")
    if args.provider == "skyfield":
        from .fixedstars.skyfield_stars import star_lonlat
        lon, lat = star_lonlat(args.name, iso)
    else:
        from .providers.se_fixedstars import fixstar_lonlat
        lon, lat = fixstar_lonlat(args.name, iso)
    print({"name": args.name, "iso": iso, "lon": lon, "lat": lat})
    return 0


def cmd_decl(args: argparse.Namespace) -> int:
    from .astro.declination import (
        antiscia_lon, contra_antiscia_lon, ecl_to_dec, is_parallel, is_contraparallel,
    )
    if args.action == "mirror":
        if args.type == "antiscia":
            print({"lon": args.lon, "antiscia": antiscia_lon(args.lon)})
        else:
            print({"lon": args.lon, "contra_antiscia": contra_antiscia_lon(args.lon)})
        return 0
    if args.action == "parallel":
        print({
            "parallel": is_parallel(args.dec1, args.dec2, args.tol),
            "contraparallel": is_contraparallel(args.dec1, args.dec2, args.tol),
        })
        return 0
    if args.action == "decl":
        print({"decl": ecl_to_dec(args.lon, args.lat)})
        return 0
    return 1


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(prog="astroengine", description="AstroEngine CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_env = sub.add_parser("env", help="Print environment diagnostics")
    _add_common_flags(p_env)
    p_env.set_defaults(fn=cmd_env)

    p_prov = sub.add_parser("provider", help="List or check providers")
    p_prov.add_argument("action", choices=["list", "check"])
    p_prov.add_argument("name", nargs="?", default="swiss")
    p_prov.set_defaults(fn=cmd_providers)

    p_star = sub.add_parser("star", help="Lookup fixed star ecliptic position")
    p_star.add_argument("name")
    p_star.add_argument("--provider", choices=["swiss", "skyfield"], default="swiss")
    p_star.add_argument("--iso", help="ISO-8601 UTC (default: now)")
    p_star.set_defaults(fn=cmd_star)

    p_decl = sub.add_parser("decl", help="Declination & antiscia utilities")
    p_decl.add_argument("action", choices=["mirror", "parallel", "decl"])
    p_decl.add_argument("--type", choices=["antiscia", "contra"], default="antiscia")
    p_decl.add_argument("--lon", type=float, default=0.0)
    p_decl.add_argument("--lat", type=float, default=0.0)
    p_decl.add_argument("--dec1", type=float, default=0.0)
    p_decl.add_argument("--dec2", type=float, default=0.0)
    p_decl.add_argument("--tol", type=float, default=0.5)
    p_decl.set_defaults(fn=cmd_decl)

    core_registrar = globals().get("_register_core_commands")
    if callable(core_registrar):
        core_registrar(sub)

    ns = ap.parse_args(argv)
    result = ns.fn(ns)
    return result if isinstance(result, int) else 0
# >>> AUTO-GEN END: AE CLI v1.2

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


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
