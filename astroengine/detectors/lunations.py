"""Lunation detector built on Swiss Ephemeris longitudes."""

from __future__ import annotations

from typing import Dict, Tuple

from .common import delta_deg, jd_to_iso, moon_lon, solve_zero_crossing, sun_lon
from ..events import LunationEvent

__all__ = ["find_lunations"]


PHASES: Dict[float, str] = {
    0.0: "new_moon",
    90.0: "first_quarter",
    180.0: "full_moon",
    270.0: "last_quarter",
}


def _elongation_offset(jd_ut: float, target_angle: float) -> float:
    """Return signed separation between current elongation and ``target_angle``."""

    elong = (moon_lon(jd_ut) - sun_lon(jd_ut)) % 360.0
    return delta_deg(elong, target_angle)


def _build_event(jd_ut: float, phase_deg: float, phase_name: str) -> LunationEvent:
    sun_long = sun_lon(jd_ut)
    moon_long = moon_lon(jd_ut)
    return LunationEvent(
        ts=jd_to_iso(jd_ut),
        jd=jd_ut,
        phase=phase_name,
        phase_deg=phase_deg,
        sun_longitude=sun_long,
        moon_longitude=moon_long,
    )


def find_lunations(start_jd: float, end_jd: float) -> list[LunationEvent]:
    """Return lunations between ``start_jd`` and ``end_jd`` (inclusive)."""

    if end_jd <= start_jd:
        return []

    state: Dict[float, Tuple[float, float]] = {}
    for phase in PHASES:
        state[phase] = (start_jd, _elongation_offset(start_jd, phase))

    events: list[LunationEvent] = []
    seen_keys: set[Tuple[str, int]] = set()

    step_days = 0.5
    current = start_jd + step_days
    while current <= end_jd + 1e-6:
        for phase_deg, phase_name in PHASES.items():
            prev_jd, prev_val = state[phase_deg]
            curr_val = _elongation_offset(current, phase_deg)
            if prev_val == 0.0:
                root = prev_jd
            elif prev_val * curr_val <= 0.0:
                try:
                    root = solve_zero_crossing(
                        lambda x, target=phase_deg: _elongation_offset(x, target),
                        prev_jd,
                        current,
                        tol_deg=1e-4,
                    )
                except ValueError:
                    state[phase_deg] = (current, curr_val)
                    continue
            else:
                state[phase_deg] = (current, curr_val)
                continue

            key = (phase_name, int(round(root * 86400)))
            if key not in seen_keys and start_jd <= root <= end_jd:
                events.append(_build_event(root, phase_deg, phase_name))
                seen_keys.add(key)
            state[phase_deg] = (current, curr_val)
        current += step_days

    events.sort(key=lambda event: event.jd)
    return events
