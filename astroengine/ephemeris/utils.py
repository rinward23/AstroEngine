
"""Utilities for resolving Swiss Ephemeris data paths."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from ..infrastructure.home import ae_home


def get_se_ephe_path(default: Optional[str] = None) -> Optional[str]:
    """Return the configured Swiss Ephemeris directory if available."""

    for env_var in ("ASTROENGINE_EPHEMERIS_PATH", "SE_EPHE_PATH"):
        candidate = os.environ.get(env_var)
        if candidate:
            return str(Path(candidate).expanduser())

    if default:
        return str(Path(default).expanduser())

    home_path = ae_home() / "ephemeris"
    if home_path.exists():
        return str(home_path)

    return None
