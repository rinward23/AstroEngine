"""Compatibility layer for :mod:`astroengine.modules.vca.catalogs`."""

from __future__ import annotations

from ..modules.vca.catalogs import (
    VCA_CENTAURS,
    VCA_CORE_BODIES,
    VCA_EXT_ASTEROIDS,
    VCA_SENSITIVE_POINTS,
    VCA_TNOS,
)

from . import sbdb

__all__ = [
    "VCA_CORE_BODIES",
    "VCA_EXT_ASTEROIDS",
    "VCA_CENTAURS",
    "VCA_TNOS",
    "VCA_SENSITIVE_POINTS",
]

__all__.append("sbdb")
