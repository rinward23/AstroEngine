"""Composite and Davison chart utilities."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Dict, Iterable, Mapping


def _norm360(x: float) -> float:
    """Normalize an angle to the [0°, 360°) range."""
    v = x % 360.0
    return v + 360.0 if v < 0.0 else v


def _wrap_minus180_to_180(x: float) -> float:
    """Wrap an angle to the (-180°, 180°] range."""
    return ((x + 180.0) % 360.0) - 180.0


def circular_midpoint(a_deg: float, b_deg: float) -> float:
    """Return the circular midpoint along the shortest arc between two angles."""
    a = float(a_deg)
    b = float(b_deg)
    d = _wrap_minus180_to_180(b - a)
    return _norm360(a + d / 2.0)


def composite_midpoint_positions(
    pos_a: Mapping[str, float],
    pos_b: Mapping[str, float],
    objects: Iterable[str],
) -> Dict[str, float]:
    """Compute midpoints for objects present in both position dictionaries."""
    out: Dict[str, float] = {}
    for name in objects:
        if name in pos_a and name in pos_b:
            out[name] = circular_midpoint(pos_a[name], pos_b[name])
    return out


PositionProvider = Callable[[datetime], Mapping[str, float]]


def davison_positions(
    objects: Iterable[str],
    dt_a: datetime,
    dt_b: datetime,
    provider: PositionProvider,
) -> Dict[str, float]:
    """Return Davison longitudes at the UTC midpoint between two datetimes."""
    a = dt_a.astimezone(timezone.utc)
    b = dt_b.astimezone(timezone.utc)
    mid = a + (b - a) / 2
    pos = provider(mid)
    return {name: _norm360(float(pos[name])) for name in objects if name in pos}
