


def cmd_env(args: argparse.Namespace) -> int:
    import importlib, os
    mods = ["pyswisseph", "numpy", "pandas"]
    missing = [m for m in mods if importlib.util.find_spec(m) is None]
    print("imports:", "ok" if not missing else f"missing={missing}")
    eph = os.environ.get("SE_EPHE_PATH") or os.environ.get("SWE_EPH_PATH")
    print("ephemeris:", eph or "(unset)")
    print("providers:", ", ".join(list_providers()) or "(none)")
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

    if args.sqlite:
        SQLiteExporter(args.sqlite).write(events)
    if args.parquet:
        ParquetExporter(args.parquet).write(events)
    return 0



def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="astroengine", description="AstroEngine CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_env = sub.add_parser("env", help="Print environment diagnostics")

    p_scan.add_argument("--moving", default="mars")
    p_scan.add_argument("--target", default="venus")
    p_scan.add_argument("--provider", default="swiss", choices=["swiss", "skyfield"])
    p_scan.add_argument("--decl-orb", type=float, default=0.5)
    p_scan.add_argument("--mirror-orb", type=float, default=2.0)


    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    ns = ap.parse_args(argv if argv is not None else sys.argv[1:])
    return int(ns.fn(ns))

if __name__ == "__main__":
    raise SystemExit(main())

