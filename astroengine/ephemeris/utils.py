"""Utility helpers for Swiss ephemeris configuration."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

__all__ = ["get_se_ephe_path"]


def get_se_ephe_path(default: Optional[str] = None) -> Optional[str]:
    """Return the configured Swiss ephemeris path if one is available."""

    for env_var in ("SE_EPHE_PATH", "SWE_EPH_PATH", "ASTROENGINE_EPHEMERIS_PATH"):
        value = os.environ.get(env_var)
        if value:
            candidate = Path(value)
            if candidate.exists():
                return str(candidate)
    return default
