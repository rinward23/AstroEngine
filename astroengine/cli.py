# >>> AUTO-GEN BEGIN: AE CLI v1.3
from __future__ import annotations
import sys
import argparse

from .providers import get_provider, list_providers
from .engine import scan_contacts
from .exporters import SQLiteExporter, ParquetExporter


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
        print(e)
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

    p_scan = sub.add_parser("scan", help="Scan window for declination/antiscia contacts")
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
