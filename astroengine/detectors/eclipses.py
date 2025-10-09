"""Eclipse detection using Swiss Ephemeris."""

from __future__ import annotations

import math
from collections.abc import Sequence

from astroengine.engine.ephe_runtime import init_ephe
from astroengine.ephemeris.swe import has_swe, swe

from ..ephemeris.cache import calc_ut_cached
from ..events import EclipseEvent
from .common import jd_to_iso, moon_lon, sun_lon

__all__ = ["find_eclipses"]

Location = tuple[float, float] | tuple[float, float, float]


def _moon_latitude(jd_ut: float) -> float:
    """Return Moon ecliptic latitude in degrees."""

    if not has_swe():
        raise RuntimeError("Swiss ephemeris not available; install astroengine[ephem]")
    flag = init_ephe() | swe().FLG_SPEED
    xx, ret_flag = calc_ut_cached(jd_ut, int(swe().MOON), flag)
    if ret_flag < 0:
        raise RuntimeError(f"Swiss ephemeris returned error code {ret_flag}")
    if len(xx) < 2:
        raise RuntimeError("Swiss ephemeris did not return latitude component")
    return float(xx[1])


def _normalize_location(
    location: Location | Sequence[float] | None,
) -> tuple[float, float, float] | None:
    if location is None:
        return None
    seq = tuple(float(x) for x in location)  # type: ignore[arg-type]
    if len(seq) < 2:
        raise ValueError("location must provide longitude and latitude")
    lon, lat = seq[0], seq[1]
    alt = seq[2] if len(seq) > 2 else 0.0
    return (lon, lat, alt)


def _visible_at_location(
    jd_ut: float, eclipse_type: str, location: tuple[float, float, float] | None
) -> bool | None:
    if not has_swe() or location is None:
        return None

    lon, lat, alt = location
    geopos = (lon, lat, alt)
    flags = init_ephe()
    start = jd_ut - 0.5

    try:
        if eclipse_type == "solar":
            retflag, tret, _ = swe().sol_eclipse_when_loc(start, geopos, flags)
        else:
            retflag, tret, _ = swe().lun_eclipse_when_loc(start, geopos, flags)
    except Exception:
        return None

    if retflag == 0:
        return False

    max_time = float(tret[0]) if tret else float("nan")
    if math.isnan(max_time) or abs(max_time - jd_ut) > 1.0:
        return False

    return bool(retflag & swe().ECL_VISIBLE)


def _solar_eclipses(
    start_jd: float,
    end_jd: float,
    location: tuple[float, float, float] | None,
) -> list[EclipseEvent]:
    events: list[EclipseEvent] = []
    jd = start_jd
    flags = init_ephe()

    while True:
        retflag, tret = swe().sol_eclipse_when_glob(jd, flags)
        if retflag == 0:
            break
        max_jd = float(tret[0])
        if max_jd > end_jd:
            break
        if max_jd < start_jd:
            jd = max_jd + 1.0
            continue

        visible = _visible_at_location(max_jd, "solar", location)
        events.append(
            EclipseEvent(
                ts=jd_to_iso(max_jd),
                jd=max_jd,
                eclipse_type="solar",
                phase="new_moon",
                sun_longitude=sun_lon(max_jd) % 360.0,
                moon_longitude=moon_lon(max_jd) % 360.0,
                moon_latitude=_moon_latitude(max_jd),
                is_visible=visible,
            )
        )

        jd = max_jd + 1.0

    return events


def _lunar_eclipses(
    start_jd: float,
    end_jd: float,
    location: tuple[float, float, float] | None,
) -> list[EclipseEvent]:
    events: list[EclipseEvent] = []
    jd = start_jd
    flags = init_ephe()

    while True:
        retflag, tret = swe().lun_eclipse_when(jd, flags)
        if retflag == 0:
            break
        max_jd = float(tret[0])
        if max_jd > end_jd:
            break
        if max_jd < start_jd:
            jd = max_jd + 1.0
            continue

        visible = _visible_at_location(max_jd, "lunar", location)
        events.append(
            EclipseEvent(
                ts=jd_to_iso(max_jd),
                jd=max_jd,
                eclipse_type="lunar",
                phase="full_moon",
                sun_longitude=sun_lon(max_jd) % 360.0,
                moon_longitude=moon_lon(max_jd) % 360.0,
                moon_latitude=_moon_latitude(max_jd),
                is_visible=visible,
            )
        )

        jd = max_jd + 1.0

    return events


def find_eclipses(
    start_jd: float,
    end_jd: float,
    *,
    location: Location | Sequence[float] | None = None,
) -> list[EclipseEvent]:
    """Return solar and lunar eclipses in the supplied range."""

    if end_jd <= start_jd:
        return []
    if swe is None:
        raise RuntimeError("Swiss ephemeris not available; install astroengine[ephem]")

    loc = _normalize_location(location)
    events = _solar_eclipses(start_jd, end_jd, loc) + _lunar_eclipses(
        start_jd, end_jd, loc
    )
    events.sort(key=lambda event: event.jd)
    return events
