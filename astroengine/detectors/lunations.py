"""Lunation detector built on Swiss Ephemeris longitudes."""

from __future__ import annotations

from typing import Dict

from ..events import LunationEvent
from .common import delta_deg, jd_to_iso, moon_lon, solve_zero_crossing, sun_lon

__all__ = ["find_lunations"]

_PHASE_TARGETS: Dict[str, float] = {"new_moon": 0.0, "full_moon": 180.0}


def _synodic_phase(jd_ut: float) -> float:
    """Return the Moon-Sun phase angle in degrees (0–360)."""

    return (moon_lon(jd_ut) - sun_lon(jd_ut)) % 360.0


def _phase_delta(jd_ut: float, target: float) -> float:
    phase = _synodic_phase(jd_ut)
    return delta_deg(phase, target)


def find_lunations(
    start_jd: float,
    end_jd: float,
    *,
    step_hours: float = 6.0,
) -> list[LunationEvent]:
    """Return lunation events between ``start_jd`` and ``end_jd`` inclusive."""

    if end_jd <= start_jd:
        return []

    step_days = step_hours / 24.0
    events: list[LunationEvent] = []

    prev_jd = start_jd
    prev_deltas = {
        phase: _phase_delta(prev_jd, target) for phase, target in _PHASE_TARGETS.items()
    }

    jd = start_jd + step_days
    while jd <= end_jd + step_days:
        curr_deltas = {
            phase: _phase_delta(jd, target) for phase, target in _PHASE_TARGETS.items()
        }

        for phase, target in _PHASE_TARGETS.items():
            prev_delta = prev_deltas[phase]
            curr_delta = curr_deltas[phase]
            root: float | None = None

            if prev_delta == 0.0:
                root = prev_jd
            elif prev_delta * curr_delta <= 0.0:
                try:
                    root = solve_zero_crossing(
                        lambda x, t=target: _phase_delta(x, t),
                        prev_jd,
                        min(jd, end_jd),
                        tol=1e-5,
                        tol_deg=1e-4,
                    )
                except ValueError:
                    root = None

            if root is None or not (start_jd <= root <= end_jd):
                continue

            sun = sun_lon(root) % 360.0
            moon = moon_lon(root) % 360.0
            events.append(
                LunationEvent(
                    ts=jd_to_iso(root),
                    jd=root,
                    phase=phase,
                    sun_longitude=sun,
                    moon_longitude=moon,
                )
            )

        prev_jd = jd
        prev_deltas = curr_deltas
        jd += step_days

    events.sort(key=lambda event: event.jd)

    unique: list[LunationEvent] = []
    seen_keys: set[tuple[str, int]] = set()
    for event in events:
        key = (event.phase, int(round(event.jd * 86400)))
        if key in seen_keys:
            continue
        seen_keys.add(key)
        unique.append(event)

    return unique
