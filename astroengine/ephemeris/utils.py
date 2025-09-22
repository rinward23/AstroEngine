# >>> AUTO-GEN BEGIN: Ephemeris Utils v1.0
from __future__ import annotations

import os
from pathlib import Path

__all__ = ["get_se_ephe_path"]


def get_se_ephe_path() -> str:
    """Return the Swiss Ephemeris path derived from environment hints."""

    explicit = os.environ.get("SE_EPHE_PATH") or os.environ.get("ASTROENGINE_SWE_PATH")
    if explicit:
        return str(Path(explicit).expanduser())
    cache_root = Path(os.environ.get("ASTROENGINE_CACHE", Path.home() / ".astroengine"))
    return str(cache_root / "swiss")
