"""Timeline utilities exposing lunations, eclipses, stations, and void-of-course data."""

from __future__ import annotations

import datetime as dt
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ..detectors.common import body_lon, delta_deg, moon_lon, solve_zero_crossing
from ..detectors.eclipses import find_eclipses as _detector_eclipses
from ..detectors.ingresses import sign_index, sign_name
from ..detectors.lunations import find_lunations as _detector_lunations
from ..detectors.stations import find_stations as _detector_stations
from ..ephemeris.swisseph_adapter import SwissEphemerisAdapter
from ..events import EclipseEvent, LunationEvent, StationEvent

__all__ = [
    "find_lunations",
    "find_eclipses",
    "find_stations",
    "void_of_course_moon",
    "VoidOfCourseEvent",
]

_VOC_ASPECTS: Mapping[str, float] = {
    "conjunction": 0.0,
    "sextile": 60.0,
    "square": 90.0,
    "trine": 120.0,
    "opposition": 180.0,
}
_VOC_BODIES: Sequence[str] = (
    "Sun",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
)


@dataclass(frozen=True)
class VoidOfCourseEvent:
    """Represents a void-of-course Moon interval."""

    ts: str
    jd: float
    end_ts: str
    end_jd: float
    is_void: bool
    moon_sign: str
    next_sign: str
    end_reason: str
    terminating_body: str | None = None
    terminating_aspect: str | None = None


def _ensure_utc(moment: dt.datetime) -> dt.datetime:
    if moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None:
        raise ValueError("datetime must be timezone-aware in UTC")
    return moment.astimezone(dt.UTC)


def _to_julian(moment: dt.datetime) -> float:
    adapter = SwissEphemerisAdapter.get_default_adapter()
    return adapter.julian_day(_ensure_utc(moment))


def _from_julian(jd: float) -> dt.datetime:
    adapter = SwissEphemerisAdapter.get_default_adapter()
    return adapter.from_julian_day(jd)


def find_lunations(
    start: dt.datetime,
    end: dt.datetime,
    *,
    step_hours: float = 3.0,
) -> list[LunationEvent]:
    """Return lunations between ``start`` and ``end`` using Swiss ephemeris."""

    start_jd = _to_julian(start)
    end_jd = _to_julian(end)
    return _detector_lunations(start_jd, end_jd, step_hours=step_hours)


def find_eclipses(start: dt.datetime, end: dt.datetime) -> list[EclipseEvent]:
    """Return eclipses between ``start`` and ``end`` when Swiss ephemeris is available."""

    start_jd = _to_julian(start)
    end_jd = _to_julian(end)
    return _detector_eclipses(start_jd, end_jd)


def find_stations(
    body: str,
    start: dt.datetime,
    end: dt.datetime,
    *,
    step_days: float = 0.5,
) -> list[StationEvent]:
    """Return station events for ``body`` within ``start`` and ``end``."""

    start_jd = _to_julian(start)
    end_jd = _to_julian(end)
    events = _detector_stations(start_jd, end_jd, bodies=[body], step_days=step_days)
    return events


def _moon_sign_boundary(longitude: float, *, sign_orb: float) -> float:
    idx = sign_index(longitude)
    boundary = (idx + 1) * 30.0
    return boundary + float(sign_orb)


def _refine_moon_ingress(start_jd: float, *, sign_orb: float) -> float:
    start_lon = moon_lon(start_jd) % 360.0
    target = _moon_sign_boundary(start_lon, sign_orb=sign_orb)
    prev_jd = start_jd
    prev_delta = delta_deg(moon_lon(prev_jd), target)
    step = 1.0 / 24.0  # 1 hour steps
    jd = prev_jd + step
    limit = start_jd + 3.0
    while jd <= limit:
        curr_delta = delta_deg(moon_lon(jd), target)
        root: float | None = None
        if prev_delta == 0.0:
            root = prev_jd
        elif prev_delta * curr_delta <= 0.0:
            try:
                root = solve_zero_crossing(
                    lambda value, tgt=target: delta_deg(moon_lon(value), tgt),
                    prev_jd,
                    jd,
                    tol=5e-6,
                    value_tol=5e-5,
                )
            except ValueError:
                root = None
        if root is not None and root > start_jd:
            return root
        prev_jd = jd
        prev_delta = curr_delta
        jd += step
    return limit


def _aspect_delta(jd: float, body: str, target: float) -> float:
    moon = moon_lon(jd)
    other = body_lon(jd, body)
    separation = (moon - other) % 360.0
    return delta_deg(separation, target)


def _next_moon_aspect(start_jd: float, end_jd: float) -> tuple[float, str, str] | None:
    if end_jd <= start_jd:
        return None
    step = 1.0 / 24.0
    prev_jd = start_jd
    prev = {
        body: {name: _aspect_delta(prev_jd, body, angle) for name, angle in _VOC_ASPECTS.items()}
        for body in _VOC_BODIES
    }
    jd = start_jd + step
    while jd <= end_jd:
        curr = {
            body: {name: _aspect_delta(jd, body, angle) for name, angle in _VOC_ASPECTS.items()}
            for body in _VOC_BODIES
        }
        candidate: tuple[float, str, str] | None = None
        for body in _VOC_BODIES:
            for aspect_name, target in _VOC_ASPECTS.items():
                prev_delta = prev[body][aspect_name]
                curr_delta = curr[body][aspect_name]
                root: float | None = None
                if prev_delta == 0.0:
                    root = prev_jd
                elif prev_delta * curr_delta <= 0.0:
                    try:
                        root = solve_zero_crossing(
                            lambda value, b=body, t=target: _aspect_delta(value, b, t),
                            prev_jd,
                            min(jd, end_jd),
                            tol=5e-6,
                            value_tol=5e-5,
                        )
                    except ValueError:
                        root = None
                if root is None or not (start_jd <= root <= end_jd):
                    continue
                if candidate is None or root < candidate[0]:
                    candidate = (root, body, aspect_name)
        if candidate is not None:
            return candidate
        prev_jd = jd
        prev = curr
        jd += step
    return None


def void_of_course_moon(
    moment: dt.datetime,
    *,
    sign_orb: float = 0.0,
) -> VoidOfCourseEvent:
    """Return a naive void-of-course Moon interval beginning at ``moment``."""

    start_dt = _ensure_utc(moment)
    start_jd = _to_julian(start_dt)
    start_lon = moon_lon(start_jd) % 360.0
    ingress_jd = _refine_moon_ingress(start_jd, sign_orb=sign_orb)
    aspect = _next_moon_aspect(start_jd, ingress_jd)
    is_void = aspect is None
    end_jd = ingress_jd if is_void else aspect[0]
    end_dt = _from_julian(end_jd)
    return VoidOfCourseEvent(
        ts=start_dt.isoformat().replace("+00:00", "Z"),
        jd=start_jd,
        end_ts=end_dt.astimezone(dt.UTC).isoformat().replace("+00:00", "Z"),
        end_jd=end_jd,
        is_void=is_void,
        moon_sign=sign_name(sign_index(start_lon)),
        next_sign=sign_name(sign_index(start_lon) + 1),
        end_reason="ingress" if is_void else "aspect",
        terminating_body=None if is_void else aspect[1],
        terminating_aspect=None if is_void else aspect[2],
    )
