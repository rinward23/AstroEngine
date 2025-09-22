"""Eclipse detection using Swiss Ephemeris."""

from __future__ import annotations

try:  # pragma: no cover - exercised via runtime availability checks
    import swisseph as swe  # type: ignore
except Exception:  # pragma: no cover
    swe = None  # type: ignore

from .common import jd_to_iso, moon_lon
from .lunations import find_lunations
from ..events import EclipseEvent

__all__ = ["find_eclipses"]


def _moon_latitude(jd_ut: float) -> float:
    """Return Moon ecliptic latitude in degrees."""

    if swe is None:
        raise RuntimeError("Swiss ephemeris not available; install astroengine[ephem]")
    moon_lon(jd_ut)
    values, _ = swe.calc_ut(jd_ut, swe.MOON, swe.FLG_SWIEPH | swe.FLG_SPEED)
    if len(values) < 2:
        raise RuntimeError("Swiss ephemeris did not return latitude component")
    return float(values[1])


def find_eclipses(
    start_jd: float,
    end_jd: float,
    *,
    latitude_threshold: float = 1.5,
) -> list[EclipseEvent]:
    """Return solar and lunar eclipses in the supplied range."""

    if end_jd <= start_jd:
        return []
    if swe is None:
        raise RuntimeError("Swiss ephemeris not available; install astroengine[ephem]")

    events: list[EclipseEvent] = []
    for lunation in find_lunations(start_jd - 5.0, end_jd + 5.0):
        if not (start_jd <= lunation.jd <= end_jd):
            continue
        if lunation.phase not in {"new_moon", "full_moon"}:
            continue

        lat = _moon_latitude(lunation.jd)
        if abs(lat) > latitude_threshold:
            continue

        eclipse_type = "solar" if lunation.phase == "new_moon" else "lunar"
        events.append(
            EclipseEvent(
                ts=jd_to_iso(lunation.jd),
                jd=lunation.jd,
                eclipse_type=eclipse_type,
                phase=lunation.phase,
                sun_longitude=lunation.sun_longitude,
                moon_longitude=lunation.moon_longitude,
                moon_latitude=lat,
            )
        )

    events.sort(key=lambda event: event.jd)
    return events
