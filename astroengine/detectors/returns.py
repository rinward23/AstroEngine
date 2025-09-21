# >>> AUTO-GEN BEGIN: detector-returns v2.0
from __future__ import annotations
from typing import Callable, List

from .common import delta_deg, jd_to_iso, moon_lon, refine_zero_secant_bisect, sun_lon
from ..events import ReturnEvent

_STEP_DAYS = 1.0


def _body_lon_func(which: str):
    if which == "solar":
        return sun_lon
    if which == "lunar":
        return moon_lon
    raise ValueError(f"Unsupported return kind: {which}")


def _difference_func(which: str, target: float) -> Callable[[float], float]:
    lon_fn = _body_lon_func(which)
    return lambda jd: delta_deg(lon_fn(jd), target)


def solar_lunar_returns(
    natal_jd: float,
    start_jd: float,
    end_jd: float,
    which: str = "solar",
) -> List[ReturnEvent]:
    which = which.lower()
    if start_jd >= end_jd:
        return []
    lon_fn = _body_lon_func(which)
    target_lon = lon_fn(natal_jd)
    diff_fn = _difference_func(which, target_lon)
    events: List[ReturnEvent] = []

    prev_jd = start_jd
    prev_val = diff_fn(prev_jd)
    jd = start_jd + _STEP_DAYS
    while jd <= end_jd + _STEP_DAYS:
        curr_val = diff_fn(jd)
        root: float | None = None
        if prev_val == 0.0:
            root = prev_jd
        elif curr_val == 0.0:
            root = jd
        elif (prev_val > 0 and curr_val < 0) or (prev_val < 0 and curr_val > 0):
            root = refine_zero_secant_bisect(diff_fn, prev_jd, jd)
        if root is not None and start_jd <= root <= end_jd:
            iso = jd_to_iso(root)
            events.append(ReturnEvent(kind=which, body=which.title(), ts=iso, longitude=lon_fn(root)))
        prev_jd = jd
        prev_val = curr_val
        jd += _STEP_DAYS
    events.sort(key=lambda e: e.ts)
    return events
# >>> AUTO-GEN END: detector-returns v2.0
