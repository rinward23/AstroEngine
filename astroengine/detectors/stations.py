"""Planetary station detector backed by Swiss ephemeris speeds."""

from __future__ import annotations

from typing import Mapping, Optional, Sequence

try:  # pragma: no cover - optional dependency guard
    import swisseph as swe  # type: ignore
except Exception:  # pragma: no cover
    swe = None  # type: ignore

from .common import body_lon, jd_to_iso, solve_zero_crossing
from ..events import StationEvent

__all__ = ["find_stations"]


DEFAULT_BODIES: Sequence[str] = (
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
)


def _body_code(name: str) -> int:
    if swe is None:
        raise RuntimeError("Swiss ephemeris not available; install astroengine[ephem]")
    key = name.lower()
    mapping: Mapping[str, int] = {
        "mercury": swe.MERCURY,
        "venus": swe.VENUS,
        "mars": swe.MARS,
        "jupiter": swe.JUPITER,
        "saturn": swe.SATURN,
        "uranus": swe.URANUS,
        "neptune": swe.NEPTUNE,
        "pluto": swe.PLUTO,
    }
    return mapping[key]


def _speed(jd_ut: float, code: int) -> float:
    if swe is None:
        raise RuntimeError("Swiss ephemeris not available; install astroengine[ephem]")
    _, _, _, speed_lon, _, _ = swe.calc_ut(jd_ut, code, swe.FLG_SWIEPH | swe.FLG_SPEED)
    return float(speed_lon)


def find_stations(
    start_jd: float,
    end_jd: float,
    bodies: Optional[Sequence[str]] = None,
    *,
    step_days: float = 1.0,
) -> list[StationEvent]:
    """Return planetary stations between ``start_jd`` and ``end_jd``."""

    if end_jd <= start_jd:
        return []

    targets = tuple(bodies or DEFAULT_BODIES)
    events: list[StationEvent] = []

    for body in targets:
        if swe is None:
            raise RuntimeError("Swiss ephemeris not available; install astroengine[ephem]")
        code = _body_code(body)
        # ensure Swiss path configured
        body_lon(start_jd, body)

        prev_jd = start_jd
        prev_speed = _speed(prev_jd, code)
        current = start_jd + step_days
        while current <= end_jd + step_days:
            curr_speed = _speed(current, code)
            if prev_speed == 0.0:
                root = prev_jd
            elif prev_speed * curr_speed <= 0.0:
                try:
                    root = solve_zero_crossing(
                        lambda x, body_code=code: _speed(x, body_code),
                        prev_jd,
                        min(current, end_jd),
                        tol_deg=1e-5,
                    )
                except ValueError:
                    prev_jd, prev_speed = current, curr_speed
                    current += step_days
                    continue
            else:
                prev_jd, prev_speed = current, curr_speed
                current += step_days
                continue

            lon, _, _, _, _, _ = swe.calc_ut(root, code, swe.FLG_SWIEPH | swe.FLG_SPEED)
            before = _speed(max(start_jd, root - 0.25), code)
            after = _speed(min(end_jd, root + 0.25), code)
            motion = "direct" if after > before else "retrograde"
            events.append(
                StationEvent(
                    ts=jd_to_iso(root),
                    jd=root,
                    body=body,
                    motion=motion,
                    longitude=float(lon % 360.0),
                    speed_before=before,
                    speed_after=after,
                )
            )
            prev_jd, prev_speed = current, curr_speed
            current += step_days

    events.sort(key=lambda event: (event.jd, event.body))
    return events
