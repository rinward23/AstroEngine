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
    """Smallest signed delta from ``a``→``b`` in degrees in (-180, 180].

    When the separation is exactly 180 degrees the orientation is ambiguous.
    We resolve the tie by preserving antisymmetry: the forward direction keeps
    the next representable float below 180 degrees and the reverse direction
    receives its negation. This keeps the return value within (-180, 180]
    while ensuring ``delta(a, b) == -delta(b, a)``.
    """

    raw = b - a
    delta = (raw + 180.0) % 360.0 - 180.0
    if delta == -180.0:
        tie = math.nextafter(180.0, 0.0)
        return tie if raw >= 0.0 else -tie
    return delta


def is_within_orb(delta: float, orb_deg: float) -> bool:
    """Return ``True`` when ``delta`` lies within ``orb_deg`` of zero."""

    return abs(delta) <= abs(orb_deg)


def classify_applying_separating(
    moving_lon: float, moving_speed: float, target_lon: float
) -> str:
    """Return 'applying' if moving body heads toward target aspect, else 'separating'."""

    d = delta_angle(moving_lon, target_lon)
    return "applying" if (d * moving_speed) < 0 else "separating"
