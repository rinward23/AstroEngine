"""Shared Swiss Ephemeris import helpers."""

from __future__ import annotations

import importlib
import importlib.util
from functools import lru_cache
from types import ModuleType

__all__ = ["swe"]


@lru_cache(maxsize=1)
def swe() -> ModuleType:
    """Return the cached :mod:`swisseph` module, raising if unavailable."""

    if importlib.util.find_spec("swisseph") is None:
        raise ModuleNotFoundError(
            "swisseph is required for Swiss Ephemeris calculations. Install the "
            "'pyswisseph' extra to enable astroengine.ephemeris features."
        )
    return importlib.import_module("swisseph")
