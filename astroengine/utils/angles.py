"""Angle utilities shared across AstroEngine modules."""

from __future__ import annotations

import math

__all__ = [
    "norm360",
    "delta_angle",
    "is_within_orb",
    "classify_applying_separating",
]


def norm360(x: float) -> float:
    """Normalize angle to [0, 360)."""

    y = math.fmod(x, 360.0)
    return y + 360.0 if y < 0 else y


def delta_angle(a: float, b: float) -> float:
    """Smallest signed delta from ``a``→``b`` in degrees in (-180, 180]."""

    d = (b - a + 180.0) % 360.0 - 180.0
    return 180.0 if d == -180.0 else d


def is_within_orb(delta: float, orb_deg: float) -> bool:
    """Return ``True`` when ``delta`` lies within ``orb_deg`` of zero."""

    return abs(delta) <= abs(orb_deg)


def classify_applying_separating(moving_lon: float, moving_speed: float, target_lon: float) -> str:
    """Return 'applying' if moving body heads toward target aspect, else 'separating'."""

    d = delta_angle(moving_lon, target_lon)
    return "applying" if (d * moving_speed) < 0 else "separating"
