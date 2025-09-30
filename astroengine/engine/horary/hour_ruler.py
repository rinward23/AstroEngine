"""Planetary hour computation utilities."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from ...ephemeris.adapter import ObserverLocation
from ...ritual.timing import PLANETARY_HOUR_TABLE
from ..observational.sun import solar_cycle
from .models import GeoLocation, PlanetaryHourResult

__all__ = ["planetary_hour", "sunrise_sunset", "moonrise_moonset"]



_RISE_FLAGS = swe.BIT_DISC_CENTER | swe.BIT_NO_REFRACTION | swe.FLG_SWIEPH


def _jd_to_datetime(jd_ut: float) -> datetime:
    """Convert a Julian Day expressed in UT to a timezone-aware datetime."""

    jd = jd_ut + 0.5
    frac, integer = math.modf(jd)
    z = int(integer)
    a = z
    if z >= 2299161:
        alpha = int((z - 1867216.25) / 36524.25)
        a = z + 1 + alpha - alpha // 4
    b = a + 1524
    c = int((b - 122.1) / 365.25)
    d = int(365.25 * c)
    e = int((b - d) / 30.6001)
    day = b - d - int(30.6001 * e) + frac
    month = e - 1 if e < 14 else e - 13
    year = c - 4716 if month > 2 else c - 4715
    day_floor = int(day)
    frac_day = day - day_floor
    hours = frac_day * 24.0
    hour = int(hours)
    minutes = (hours - hour) * 60.0
    minute = int(minutes)
    seconds = round((minutes - minute) * 60.0, 6)
    second = int(seconds)
    microsecond = int((seconds - second) * 1_000_000)
    return datetime(
        year, month, day_floor, hour, minute, second, microsecond, tzinfo=UTC
    )


def _ensure_ephemeris_ready() -> None:
    SwissEphemerisAdapter.get_default_adapter()


def _next_event(
    jd_ut: float,
    flag: int,
    location: GeoLocation,
    *,
    body: int = swe.SUN,
) -> float:
    _ensure_ephemeris_ready()
    geopos = (float(location.longitude), float(location.latitude), float(location.altitude))
    res, tret = swe.rise_trans(
        jd_ut,
        body,
        flag,
        geopos,
        0.0,
        0.0,
        _RISE_FLAGS,
    )
    if res != 0:
        raise RuntimeError(
            "Swiss Ephemeris could not compute sunrise/sunset for location"
        )
    return tret[0]


def _rise_set_cycle(
    moment: datetime,
    location: GeoLocation,
    *,
    body: int,
    fallback_step: float = 0.51,
) -> tuple[datetime, datetime, datetime]:
    """Return the rise, set, and subsequent rise for ``body`` around ``moment``."""

    jd = julian_day(moment)
    prev_rise_jd = _next_event(jd - 1.0, swe.CALC_RISE, location, body=body)
    if prev_rise_jd > jd:
        prev_rise_jd = _next_event(prev_rise_jd - 1.0, swe.CALC_RISE, location, body=body)

    set_jd = _next_event(prev_rise_jd + 0.01, swe.CALC_SET, location, body=body)
    if set_jd <= prev_rise_jd:
        set_jd = _next_event(prev_rise_jd + fallback_step, swe.CALC_SET, location, body=body)

    next_rise_jd = _next_event(set_jd + 0.01, swe.CALC_RISE, location, body=body)
    if next_rise_jd <= set_jd:
        next_rise_jd = _next_event(set_jd + fallback_step, swe.CALC_RISE, location, body=body)

    return (
        _jd_to_datetime(prev_rise_jd),
        _jd_to_datetime(set_jd),
        _jd_to_datetime(next_rise_jd),
    )


def sunrise_sunset(moment: datetime, location: GeoLocation) -> tuple[datetime, datetime, datetime]:
    """Return sunrise, sunset, and next sunrise surrounding ``moment``."""

    return _rise_set_cycle(moment, location, body=swe.SUN)


def moonrise_moonset(moment: datetime, location: GeoLocation) -> tuple[datetime, datetime, datetime]:
    """Return moonrise, moonset, and next moonrise surrounding ``moment``."""

    # The Moon's diurnal cycle is shorter than the Sun's, so a tighter fallback helps
    # keep the search within the same lunation day if the direct query fails.
    return _rise_set_cycle(moment, location, body=swe.MOON, fallback_step=0.35)



def _local_weekday(dt_utc: datetime, location: GeoLocation) -> str:
    offset_hours = location.longitude / 15.0
    local_dt = dt_utc + timedelta(hours=offset_hours)
    names = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    return names[local_dt.weekday()]


def planetary_hour(moment: datetime, location: GeoLocation) -> PlanetaryHourResult:
    """Return the planetary hour ruling the supplied moment."""

    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    else:
        moment = moment.astimezone(UTC)

    sunrise_dt, sunset_dt, next_sunrise_dt = sunrise_sunset(moment, location)

    weekday = _local_weekday(sunrise_dt, location)
    sequence = PLANETARY_HOUR_TABLE[weekday]
    day_ruler = sequence[0]

    day_length = (sunset_dt - sunrise_dt).total_seconds()
    night_length = (next_sunrise_dt - sunset_dt).total_seconds()

    if not sequence:
        raise RuntimeError("Planetary hour sequence lookup failed")

    if moment < sunset_dt:
        hour_length = day_length / 12.0 if day_length > 0 else 0.0
        elapsed = (moment - sunrise_dt).total_seconds()
        if hour_length <= 0:
            index = 0
            start = sunrise_dt
        else:
            index = min(11, int(max(0.0, elapsed) // hour_length))
            start = sunrise_dt + timedelta(seconds=hour_length * index)
        end = start + timedelta(seconds=hour_length)
        ruler = sequence[index]
    else:
        hour_length = night_length / 12.0 if night_length > 0 else 0.0
        elapsed = (moment - sunset_dt).total_seconds()
        if hour_length <= 0:
            index = 12
            start = sunset_dt
        else:
            idx = min(11, int(max(0.0, elapsed) // hour_length))
            start = sunset_dt + timedelta(seconds=hour_length * idx)
            index = 12 + idx
        end = start + timedelta(seconds=hour_length)
        ruler = sequence[index]

    return PlanetaryHourResult(
        ruler=ruler,
        index=index,
        start=start,
        end=end,
        sunrise=sunrise_dt,
        sunset=sunset_dt,
        next_sunrise=next_sunrise_dt,
        day_ruler=day_ruler,
        sequence=sequence,
    )

