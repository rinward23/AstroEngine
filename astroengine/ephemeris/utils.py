"""Swiss Ephemeris path helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def get_se_ephe_path(preferred: Optional[str] = None) -> Optional[str]:
    """Resolve the Swiss Ephemeris data directory.

    The helper checks the provided path first, then the ``SWISSEPH_PATH``
    environment variable, and finally common installation locations. It returns
    ``None`` when no candidate is available so callers can fall back gracefully.
    """

    if preferred:
        candidate = Path(preferred).expanduser()
        if candidate.exists():
            return str(candidate)
    env_path = os.environ.get("SWISSEPH_PATH")
    if env_path:
        candidate = Path(env_path).expanduser()
        if candidate.exists():
            return str(candidate)
    defaults = [
        Path.home() / "swisseph",
        Path("/usr/share/ephe"),
        Path("/usr/local/share/ephe"),
    ]
    for candidate in defaults:
        if candidate.exists():
            return str(candidate)
    return None
