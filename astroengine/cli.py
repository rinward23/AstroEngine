# >>> AUTO-GEN BEGIN: AE CLI v1.4
from __future__ import annotations
import sys
import argparse
import json

from .providers import get_provider, list_providers
from .engine import scan_contacts
from .exporters import SQLiteExporter, ParquetExporter
from .domains import rollup_domain_scores


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
        print({"when": e.when_iso, "kind": e.kind, "pair": f"{e.moving}->{e.target}", "orb": round(e.orb_abs, 4), "phase": e.applying_or_separating, "score": round(e.score, 4)})
    if args.sqlite:
        SQLiteExporter(args.sqlite).write(events)
    if args.parquet:
        ParquetExporter(args.parquet).write(events)
    return 0


def cmd_report(args: argparse.Namespace) -> int:
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
    scores = rollup_domain_scores(events)
    out = {
        d_id: {
            "score": round(d.score, 6),
            "channels": {
                ch_id: {
                    "score": round(ch.score, 6),
                    "positive": round(ch.sub.get("positive").score, 6),
                    "negative": round(ch.sub.get("negative").score, 6)
                }
                for ch_id, ch in d.channels.items()
            }
        }
        for d_id, d in scores.items()
    }
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))
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

    p_scan = sub.add_parser("scan", help="Scan window for contacts (with scores)")
    p_scan.add_argument("--start", required=True)
    p_scan.add_argument("--end", required=True)
    p_scan.add_argument("--moving", default="mars")
    p_scan.add_argument("--target", default="venus")
    p_scan.add_argument("--provider", default="swiss", choices=["swiss", "skyfield"])
    p_scan.add_argument("--decl-orb", type=float, default=0.5)
    p_scan.add_argument("--mirror-orb", type=float, default=2.0)
    p_scan.add_argument("--step", type=int, default=60)
    p_scan.add_argument("--sqlite")
    p_scan.add_argument("--parquet")
    p_scan.set_defaults(fn=cmd_scan)

    p_rep = sub.add_parser("report", help="Scan + roll up into Mind/Body/Spirit domain report")
    p_rep.add_argument("--start", required=True)
    p_rep.add_argument("--end", required=True)
    p_rep.add_argument("--moving", default="mars")
    p_rep.add_argument("--target", default="venus")
    p_rep.add_argument("--provider", default="swiss", choices=["swiss", "skyfield"])
    p_rep.add_argument("--decl-orb", type=float, default=0.5)
    p_rep.add_argument("--mirror-orb", type=float, default=2.0)
    p_rep.add_argument("--step", type=int, default=60)
    p_rep.add_argument("--out", help="write JSON report to file")
    p_rep.set_defaults(fn=cmd_report)

    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    ns = ap.parse_args(argv if argv is not None else sys.argv[1:])
    return int(ns.fn(ns))

if __name__ == "__main__":
    raise SystemExit(main())
# >>> AUTO-GEN END: AE CLI v1.4
