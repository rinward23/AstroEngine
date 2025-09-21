"""Swiss Ephemeris helper utilities."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def get_se_ephe_path(default: Optional[str]) -> Optional[str]:
    """Return the Swiss Ephemeris data path from environment fallbacks."""

    path = os.environ.get("SE_EPHE_PATH") or os.environ.get("SWE_EPH_PATH")
    if path:
        expanded = Path(path).expanduser()
        return str(expanded)
    return default
