# >>> AUTO-GEN BEGIN: detector-lunations v1.0
from __future__ import annotations
from typing import Iterable, List, Tuple

from .common import (
    delta_deg,
    find_root,
    moon_lon,
    norm360,
    sun_lon,
)
from ..events import LunationEvent

_PHASES: Tuple[Tuple[str, float], ...] = (
    ("new", 0.0),
    ("first_quarter", 90.0),
    ("full", 180.0),
    ("third_quarter", 270.0),
)


def _phase_angle(jd_ut: float) -> float:
    return norm360(moon_lon(jd_ut) - sun_lon(jd_ut))


def _phase_delta(jd_ut: float, target: float) -> float:
    return delta_deg(_phase_angle(jd_ut), target)


def _bracket_iter(start: float, end: float, step: float) -> Iterable[Tuple[float, float]]:
    t = start
    while t < end:
        nxt = min(t + step, end)
        yield t, nxt
        t = nxt


def find_lunations(start_jd: float, end_jd: float) -> List[LunationEvent]:
    if end_jd <= start_jd:
        return []

    events: List[LunationEvent] = []
    step = 1.0  # one day; sufficient to bracket phase changes

    for a, b in _bracket_iter(start_jd, end_jd, step):
        for kind, phase in _PHASES:
            fa = _phase_delta(a, phase)
            fb = _phase_delta(b, phase)
            if abs(fa) < 1e-5:
                root = a
            elif abs(fb) < 1e-5:
                root = b
            elif fa * fb > 0:
                continue
            else:
                try:
                    root = find_root(lambda jd: _phase_delta(jd, phase), a, b, tol=1e-6)
                except ValueError:
                    continue
            if not (start_jd <= root <= end_jd):
                continue
            if events and abs(events[-1].ts - root) < 1e-4:
                continue
            sun_lon_val = sun_lon(root)
            moon_lon_val = moon_lon(root)
            events.append(
                LunationEvent(
                    ts=root,
                    kind=kind,
                    phase_angle=delta_deg(moon_lon_val, sun_lon_val),
                    sun_longitude=sun_lon_val,
                    moon_longitude=moon_lon_val,
                )
            )
    events.sort(key=lambda ev: ev.ts)
    return events
# >>> AUTO-GEN END: detector-lunations v1.0
