"""Load configuration bundles for the traditional timing engines."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from ..traditional.models import LifeProfile
from ..traditional.profections import SIGN_RULERS
from ..traditional.zr import PERIOD_YEARS

__all__ = ["load_traditional_profiles"]


@lru_cache(maxsize=1)
def load_traditional_profiles() -> dict[str, Any]:
    """Return profile defaults for profections, ZR, and life-lengths."""

    life_profile = LifeProfile()
    profections = {
        "default_mode": "hellenistic",
        "house_system": "whole_sign",
        "rulers": dict(SIGN_RULERS),
    }
    zr_profile = {
        "period_years": dict(PERIOD_YEARS),
        "levels": (1, 2, 3, 4),
        "lots": ("Spirit", "Fortune"),
        "loosing_of_bond": True,
    }
    life = {
        "profile": life_profile,
        "notes": {
            "lifespan_table_source": "Ptolemy Tetrabiblos III + Lilly (1647)",
            "bounds_scheme": life_profile.bounds_scheme,
        },
    }
    return {"profections": profections, "zr": zr_profile, "life": life}
