# >>> AUTO-GEN BEGIN: se-ephe-path-utils v1.0
"""Shared utilities for ephemeris providers."""
from __future__ import annotations
import os
from typing import Optional

CANON_ENV = "SE_EPHE_PATH"
ALT_ENV = "SWE_EPH_PATH"


def get_se_ephe_path(default: Optional[str] = None) -> Optional[str]:
    """Return ephemeris directory path.

    Order: explicit arg > SE_EPHE_PATH > SWE_EPH_PATH > default.
    """
    return (
        os.environ.get(CANON_ENV)
        or os.environ.get(ALT_ENV)
        or default
    )
# >>> AUTO-GEN END: se-ephe-path-utils v1.0
