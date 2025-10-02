"""Compatibility helpers for exposing the Swiss Ephemeris as ``sweph``."""

from __future__ import annotations

import importlib
import sys


def ensure_sweph_alias() -> None:
    """Ensure ``import sweph`` resolves to the installed ``swisseph`` module."""

    try:
        swisseph = importlib.import_module("swisseph")
    except ModuleNotFoundError:
        return

    if "sweph" in sys.modules:
        return

    sys.modules["sweph"] = swisseph


__all__ = ["ensure_sweph_alias"]
