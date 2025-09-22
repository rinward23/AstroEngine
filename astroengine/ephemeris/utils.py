# >>> AUTO-GEN BEGIN: Ephemeris Utils v1.0
from __future__ import annotations
import os
from pathlib import Path

def get_se_ephe_path() -> str | None:
    """
    Return the Swiss Ephemeris data directory, or None if unknown.
    Resolution order:
    1) SE_EPHE_PATH env var
    2) Common locations (~/.sweph/ephe, ~/.sweph, /usr/share/astro/se, C:\\sweph)
    """
    p = os.getenv("SE_EPHE_PATH")
    if p:
        return p
    for c in (
        Path.home() / ".sweph" / "ephe",
        Path.home() / ".sweph",
        Path("/usr/share/astro/se"),
        Path("C:/sweph"),
    ):
        if c.exists():
            return str(c)
    return None
# >>> AUTO-GEN END: Ephemeris Utils v1.0
