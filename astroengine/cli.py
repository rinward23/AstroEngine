
from __future__ import annotations
import sys

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



