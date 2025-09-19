# >>> AUTO-GEN BEGIN: AE CLI v1.1
"""AstroEngine command-line interface with provider and star utilities."""
from __future__ import annotations
import sys
import argparse
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

    ns = ap.parse_args(argv)
    return int(ns.fn(ns))

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
# >>> AUTO-GEN END: AE CLI v1.1
