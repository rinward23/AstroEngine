"""Planetary station detector backed by Swiss ephemeris speeds."""

from __future__ import annotations

from collections.abc import Sequence

try:  # pragma: no cover - exercised via runtime availability checks
    import swisseph as swe  # type: ignore
except Exception:  # pragma: no cover
    swe = None  # type: ignore

from ..events import StationEvent
from .common import jd_to_iso, solve_zero_crossing

__all__ = ["find_stations"]

_BODY_CODES = {
    "mercury": swe.MERCURY if swe is not None else None,
    "venus": swe.VENUS if swe is not None else None,
    "mars": swe.MARS if swe is not None else None,
    "jupiter": swe.JUPITER if swe is not None else None,
    "saturn": swe.SATURN if swe is not None else None,
    "uranus": swe.URANUS if swe is not None else None,
    "neptune": swe.NEPTUNE if swe is not None else None,
    "pluto": swe.PLUTO if swe is not None else None,
}


def _speed(jd_ut: float, code: int) -> float:
    values, _ = swe.calc_ut(jd_ut, code, swe.FLG_SWIEPH | swe.FLG_SPEED)
    return float(values[3])


def _longitude(jd_ut: float, code: int) -> float:
    values, _ = swe.calc_ut(jd_ut, code, swe.FLG_SWIEPH | swe.FLG_SPEED)
    return float(values[0]) % 360.0


def find_stations(
    start_jd: float,
    end_jd: float,
    bodies: Sequence[str] | None = None,
    *,
    step_days: float = 0.5,
) -> list[StationEvent]:
    """Return planetary station events between ``start_jd`` and ``end_jd``."""

    if end_jd <= start_jd:
        return []
    if swe is None:
        raise RuntimeError("Swiss ephemeris not available; install astroengine[ephem]")

    body_names = [
        b.lower() for b in (bodies if bodies is not None else _BODY_CODES.keys())
    ]

    events: list[StationEvent] = []
    seen: set[tuple[str, int]] = set()

    for name in body_names:
        code = _BODY_CODES.get(name)
        if code is None:
            continue

        prev_jd = start_jd
        prev_speed = _speed(prev_jd, code)
        current = start_jd + step_days

        while current <= end_jd + step_days:
            curr_speed = _speed(current, code)
            root: float | None = None

            if prev_speed == 0.0:
                root = prev_jd
            elif prev_speed * curr_speed <= 0.0:
                try:
                    root = solve_zero_crossing(
                        lambda x, c=code: _speed(x, c),
                        prev_jd,
                        min(current, end_jd),
                        tol=5e-6,
                        value_tol=5e-7,
                    )
                except ValueError:
                    root = None

            if root is not None and start_jd <= root <= end_jd:
                key = (name, int(round(root * 86400)))
                if key not in seen:
                    longitude = _longitude(root, code)
                    events.append(
                        StationEvent(
                            ts=jd_to_iso(root),
                            jd=root,
                            body=name.capitalize(),
                            motion="stationary",
                            longitude=longitude,
                            speed_longitude=0.0,
                        )
                    )
                    seen.add(key)

            prev_jd, prev_speed = current, curr_speed
            current += step_days

    events.sort(key=lambda event: event.jd)
    return events
