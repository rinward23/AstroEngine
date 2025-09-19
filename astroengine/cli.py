

from __future__ import annotations
import sys



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



