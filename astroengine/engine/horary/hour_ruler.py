"""Planetary hour computation utilities."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from astroengine.ephemeris.swe import has_swe, swe

if TYPE_CHECKING:  # pragma: no cover - typing aid only
    from ...ephemeris.swisseph_adapter import SwissEphemerisAdapter

_HAS_SWE = has_swe()
_SwissAdapter: type[SwissEphemerisAdapter] | None

if _HAS_SWE:  # pragma: no branch - sentinel guards runtime import
    from ...ephemeris.swisseph_adapter import (
        SwissEphemerisAdapter as _SwissEphemerisAdapter,
    )

    _SwissAdapter = _SwissEphemerisAdapter
else:  # pragma: no cover - fallback exercised when swe missing
    _SwissAdapter = None

from ...core.time import julian_day
from astroengine.engine.ephe_runtime import init_ephe
from ...ritual.timing import PLANETARY_HOUR_TABLE
from .models import GeoLocation, PlanetaryHourResult

__all__ = [
    "GeoLocation",
    "PlanetaryHourResult",
    "planetary_hour",
    "sunrise_sunset",
    "moonrise_moonset",
]



def _rise_flags() -> int:
    if not _HAS_SWE:
        return 0
    swe_module = swe()
    base = init_ephe()
    return int(base | swe_module.BIT_DISC_CENTER | swe_module.BIT_NO_REFRACTION)


def _moon_flags() -> int:
    return _rise_flags()



def _normalize_moment(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


def _ensure_adapter(
    adapter: SwissEphemerisAdapter | None,
) -> SwissEphemerisAdapter:
    if adapter is not None:
        return adapter

    adapter_cls = _SwissAdapter
    if adapter_cls is None:
        raise RuntimeError(
            "Swiss Ephemeris support is required for rise/transit calculations"
        )
    return adapter_cls.get_default_adapter()



def _next_event(
    adapter: SwissEphemerisAdapter,
    jd_ut: float,
    event: str,
    location: GeoLocation,
    *,
    body_code: int,
    body_name: str,
    flags: int | None = None,
) -> float:
    result = adapter.rise_transit(
        jd_ut,
        body_code,
        latitude=location.latitude,
        longitude=location.longitude,
        elevation=location.altitude,
        event=event,
        flags=_rise_flags() if flags is None else flags,
        body_name=body_name,
    )
    if result.status != 0 or result.julian_day is None:
        label = body_name or "body"
        raise RuntimeError(
            f"Swiss Ephemeris could not compute {label.lower()} {event} for location"
        )
    return float(result.julian_day)



def sunrise_sunset(
    moment: datetime,
    location: GeoLocation,
    *,
    adapter: SwissEphemerisAdapter | None = None,
) -> tuple[datetime, datetime, datetime]:
    """Return sunrise, sunset, and next sunrise surrounding ``moment``."""

    resolved_adapter = _ensure_adapter(adapter)
    jd = julian_day(moment)
    flags = _rise_flags()
    prev_sunrise_jd = _next_event(
        resolved_adapter,
        jd - 1.0,
        "rise",
        location,
        body_code=swe().SUN,
        body_name="Sun",
        flags=flags,
    )
    sunset_jd = _next_event(
        resolved_adapter,
        prev_sunrise_jd + 0.01,
        "set",
        location,
        body_code=swe().SUN,
        body_name="Sun",
        flags=flags,
    )
    next_sunrise_jd = _next_event(
        resolved_adapter,
        prev_sunrise_jd + 0.51,
        "rise",
        location,
        body_code=swe().SUN,
        body_name="Sun",
        flags=flags,
    )
    sunrise_dt = resolved_adapter.from_julian_day(prev_sunrise_jd)
    sunset_dt = resolved_adapter.from_julian_day(sunset_jd)
    next_sunrise_dt = resolved_adapter.from_julian_day(next_sunrise_jd)

    return sunrise_dt, sunset_dt, next_sunrise_dt


def moonrise_moonset(
    moment: datetime,
    location: GeoLocation,
    *,
    adapter: SwissEphemerisAdapter | None = None,
) -> tuple[datetime, datetime, datetime]:
    """Return moonrise, moonset, and next moonrise surrounding ``moment``."""

    normalized = _normalize_moment(moment)

    resolved_adapter = _ensure_adapter(adapter)
    jd = resolved_adapter.julian_day(normalized)
    flags = _moon_flags()
    prev_rise = _next_event(
        resolved_adapter,
        jd - 1.0,
        "rise",
        location,
        body_code=swe().MOON,
        body_name="Moon",
        flags=flags,
    )
    set_jd = _next_event(
        resolved_adapter,
        prev_rise + 0.01,
        "set",
        location,
        body_code=swe().MOON,
        body_name="Moon",
        flags=flags,
    )
    next_rise = _next_event(
        resolved_adapter,
        prev_rise + 0.51,
        "rise",
        location,
        body_code=swe().MOON,
        body_name="Moon",
        flags=flags,
    )
    return (
        resolved_adapter.from_julian_day(prev_rise),
        resolved_adapter.from_julian_day(set_jd),
        resolved_adapter.from_julian_day(next_rise),
    )



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

    adapter = _SwissAdapter.get_default_adapter() if _SwissAdapter else None
    sunrise_dt, sunset_dt, next_sunrise_dt = sunrise_sunset(
        moment, location, adapter=adapter
    )

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

