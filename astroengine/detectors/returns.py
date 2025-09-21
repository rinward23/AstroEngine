# >>> AUTO-GEN BEGIN: detector-returns v2.0
from __future__ import annotations
from typing import List
from .common import jd_to_iso, sun_lon, moon_lon, delta_deg, refine_zero_secant_bisect


def _lon_fn(which: str):
    w = which.lower()
    if w == "solar" or w == "sun":
        return sun_lon
    if w == "lunar" or w == "moon":
        return moon_lon
    raise ValueError("which must be 'solar' or 'lunar'")


def solar_lunar_returns(natal_jd_ut: float, start_ut: float, end_ut: float, which: str = "solar") -> List["ReturnEvent"]:
    from ..events import ReturnEvent
    if start_ut >= end_ut:
        return []
    lon_fn = _lon_fn(which)
    target = lon_fn(natal_jd_ut)
    out: List[ReturnEvent] = []
    step = 1.0 if which == "solar" else 0.25  # Moon laps monthly
    jd = start_ut
    f = lambda t: delta_deg(lon_fn(t), target)
    while jd < end_ut:
        jd_next = min(jd + step, end_ut)
        fa, fb = f(jd), f(jd_next)
        if (fa == 0.0) or (fb == 0.0) or (fa > 0 and fb < 0) or (fa < 0 and fb > 0):
            t = refine_zero_secant_bisect(f, jd, jd_next, tol_deg=1e-5)
            out.append(ReturnEvent(body=which.lower(), ts=jd_to_iso(t)))
        jd = jd_next
    out.sort(key=lambda e: e.ts)
    return out
# >>> AUTO-GEN END: detector-returns v2.0
