# >>> AUTO-GEN BEGIN: detector-lunations v2.0
from __future__ import annotations
from typing import List, Tuple
from .common import jd_to_iso, delta_deg, norm360, refine_zero_secant_bisect, sun_lon, moon_lon

# Targets for elongation (Moon - Sun)
_TARGETS: List[Tuple[str, float]] = [
    ("new", 0.0),
    ("first_quarter", 90.0),
    ("full", 180.0),
    ("last_quarter", 270.0),
]


def _f_elong(target: float):
    return lambda jd: delta_deg(moon_lon(jd) - sun_lon(jd), target)


def find_lunations(start_ut: float, end_ut: float) -> List["LunationEvent"]:
    from ..events import LunationEvent
    if start_ut >= end_ut:
        return []
    out: List[LunationEvent] = []
    step = 0.5  # days; safe to bracket quarters (~7.38d spacing)
    jd = start_ut
    while jd < end_ut:
        jd_next = min(jd + step, end_ut)
        for kind, ang in _TARGETS:
            f = _f_elong(ang)
            a, b = jd, jd_next
            fa, fb = f(a), f(b)
            # Bracket if sign change or near-zero at either end
            if (fa == 0.0) or (fb == 0.0) or (fa > 0 and fb < 0) or (fa < 0 and fb > 0) or (abs(fa) < 5.0 and abs(fb) < 5.0 and abs(fa - fb) > 5.0):
                t = refine_zero_secant_bisect(f, a, b, tol_deg=1e-4)
                ts = jd_to_iso(t)
                lon_m = norm360(moon_lon(t))
                lon_s = norm360(sun_lon(t))
                out.append(LunationEvent(kind=kind, ts=ts, lon_moon=lon_m, lon_sun=lon_s))
        jd = jd_next
    # Sort & de-dup within 3 hours (rare double-detection at boundaries)
    out.sort(key=lambda e: e.ts)
    dedup: List[LunationEvent] = []
    def _parse(ts: str):
        from datetime import datetime, timezone
        return datetime.fromisoformat(ts.replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
    for e in out:
        if not dedup:
            dedup.append(e)
            continue
        dt_prev = _parse(dedup[-1].ts)
        dt_cur = _parse(e.ts)
        if (dt_cur - dt_prev).total_seconds() > 3 * 3600:
            dedup.append(e)
    return dedup
# >>> AUTO-GEN END: detector-lunations v2.0
