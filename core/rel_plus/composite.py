from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Dict, Iterable

import math

Positions = Dict[str, float]
PositionProvider = Callable[[datetime], Dict[str, float]]


def _norm360(value: float) -> float:
    v = float(value) % 360.0
    return v + 360.0 if v < 0 else v


def _circular_midpoint(a: float, b: float) -> float:
    a_n = _norm360(a)
    b_n = _norm360(b)
    ax = math.cos(math.radians(a_n))
    ay = math.sin(math.radians(a_n))
    bx = math.cos(math.radians(b_n))
    by = math.sin(math.radians(b_n))
    x = ax + bx
    y = ay + by
    if abs(x) < 1e-9 and abs(y) < 1e-9:
        return (a_n + b_n) / 2.0 % 360.0
    ang = math.degrees(math.atan2(y, x)) % 360.0
    return ang


def composite_midpoint_positions(pos_a: Positions, pos_b: Positions, objects: Iterable[str]) -> Positions:
    """Return circular midpoints for the requested objects."""

    result: Positions = {}
    missing: list[str] = []
    for name in objects:
        if name not in pos_a or name not in pos_b:
            missing.append(name)
            continue
        result[name] = _circular_midpoint(pos_a[name], pos_b[name])
    if missing:
        raise ValueError(f"Missing positions for: {', '.join(sorted(missing))}")
    return result


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _midpoint_time(dt_a: datetime, dt_b: datetime) -> datetime:
    ua = _utc(dt_a)
    ub = _utc(dt_b)
    return ua + (ub - ua) / 2


def davison_positions(objects: Iterable[str], dt_a: datetime, dt_b: datetime, provider: PositionProvider) -> Positions:
    """Return Davison composite positions at the time midpoint."""

    midpoint = _midpoint_time(dt_a, dt_b)
    state = provider(midpoint)
    if not isinstance(state, dict):
        raise TypeError("position provider must return a mapping of positions")
    missing = [name for name in objects if name not in state]
    if missing:
        raise ValueError(f"Provider missing positions for: {', '.join(sorted(missing))}")
    return {name: float(state[name]) for name in objects}


__all__ = [
    "composite_midpoint_positions",
    "davison_positions",
]
