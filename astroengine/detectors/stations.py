# >>> AUTO-GEN BEGIN: detector-stations v2.0
from __future__ import annotations
from typing import List
from .common import jd_to_iso, body_lon, delta_deg, refine_zero_secant_bisect

_DEF_BODIES = ["mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto"]


def _rate(jd: float, body: str, h: float = 0.25) -> float:
    # central difference degrees/day with wrap handling
    la = body_lon(jd - h, body)
    lb = body_lon(jd + h, body)
    return delta_deg(lb, la) / (2.0 * h)


def find_stations(start_ut: float, end_ut: float, bodies: List[str] | None = None) -> List["StationEvent"]:
    from ..events import StationEvent
    bodies = bodies or _DEF_BODIES
    out: List[StationEvent] = []
    step = 1.0  # days; stations span days, this brackets well
    for b in bodies:
        jd = start_ut
        prev = _rate(jd, b)
        while jd < end_ut:
            jd_next = min(jd + step, end_ut)
            cur = _rate(jd_next, b)
            if (prev == 0.0) or (cur == 0.0) or (prev > 0 and cur < 0) or (prev < 0 and cur > 0):
                # refine zero of rate function
                f = lambda t: _rate(t, b)
                t = refine_zero_secant_bisect(f, jd, jd_next, tol_deg=1e-6)
                # Determine kind by inspecting rate epsilon after
                eps = _rate(t + 0.02, b)
                kind = "station_rx" if eps < 0 else "station_dx"
                out.append(StationEvent(body=b.capitalize(), kind=kind, ts=jd_to_iso(t)))
            jd, prev = jd_next, cur
    out.sort(key=lambda e: e.ts)
    return out
# >>> AUTO-GEN END: detector-stations v2.0
