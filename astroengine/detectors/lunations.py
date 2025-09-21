# >>> AUTO-GEN BEGIN: detector-lunations v2.0
from __future__ import annotations
from typing import Callable, Dict, List, Tuple

from .common import (
    delta_deg,
    jd_to_iso,
    moon_lon,
    norm360,
    refine_zero_secant_bisect,
    sun_lon,
)
from ..events import LunationEvent

_LUNATION_TARGETS: Tuple[Tuple[str, float], ...] = (
    ("new", 0.0),
    ("first_quarter", 90.0),
    ("full", 180.0),
    ("last_quarter", 270.0),
)
_STEP_DAYS = 1.0


def _elongation(jd_ut: float) -> float:
    return norm360(moon_lon(jd_ut) - sun_lon(jd_ut))


def _delta_to_target(jd_ut: float, target: float) -> float:
    return delta_deg(_elongation(jd_ut), target)


def find_lunations(start_jd: float, end_jd: float) -> List[LunationEvent]:
    if start_jd >= end_jd:
        return []
    events: List[LunationEvent] = []
    prev_jd: Dict[str, float] = {}
    prev_val: Dict[str, float] = {}
    last_iso: Dict[str, str | None] = {kind: None for kind, _ in _LUNATION_TARGETS}

    initial_elong = _elongation(start_jd)
    for kind, target in _LUNATION_TARGETS:
        prev_jd[kind] = start_jd
        prev_val[kind] = delta_deg(initial_elong, target)

    jd = start_jd + _STEP_DAYS
    while jd <= end_jd + _STEP_DAYS:
        elong = _elongation(jd)
        for kind, target in _LUNATION_TARGETS:
            prev_value = prev_val[kind]
            curr_value = delta_deg(elong, target)
            root_jd: float | None = None
            if prev_value == 0.0:
                root_jd = prev_jd[kind]
            elif curr_value == 0.0:
                root_jd = jd
            elif (prev_value > 0 and curr_value < 0) or (prev_value < 0 and curr_value > 0):
                func: Callable[[float], float] = lambda x, t=target: _delta_to_target(x, t)
                root_jd = refine_zero_secant_bisect(func, prev_jd[kind], jd)
            if root_jd is not None and start_jd <= root_jd <= end_jd:
                iso = jd_to_iso(root_jd)
                if last_iso[kind] != iso:
                    s_lon = sun_lon(root_jd)
                    m_lon = moon_lon(root_jd)
                    events.append(
                        LunationEvent(
                            kind=kind,
                            ts=iso,
                            sun_lon=s_lon,
                            moon_lon=m_lon,
                            elongation=norm360(m_lon - s_lon),
                        )
                    )
                    last_iso[kind] = iso
            prev_jd[kind] = jd
            prev_val[kind] = curr_value
        jd += _STEP_DAYS
    events.sort(key=lambda e: e.ts)
    return events
# >>> AUTO-GEN END: detector-lunations v2.0
