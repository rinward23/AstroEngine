"""Planetary hour computation utilities."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

try:  # pragma: no cover - Swiss Ephemeris is optional in some environments
    import swisseph as swe
except ModuleNotFoundError:  # pragma: no cover - tests exercise fallback path
    swe = None  # type: ignore[assignment]

if swe is not None:  # pragma: no branch - sentinel guards runtime import
    from ...ephemeris.swisseph_adapter import SwissEphemerisAdapter as _SwissAdapter
else:  # pragma: no cover - fallback exercised when swe missing
    _SwissAdapter = None  # type: ignore[assignment]

if TYPE_CHECKING:  # pragma: no cover - typing aid only
    from ...ephemeris.swisseph_adapter import SwissEphemerisAdapter

if _SwissAdapter is not None:
    SwissEphemerisAdapter = _SwissAdapter
else:  # pragma: no cover - ensures attribute exists for typing tools
    SwissEphemerisAdapter = None  # type: ignore[assignment]

from ...core.time import julian_day
from ...ephemeris.swisseph_adapter import SwissEphemerisAdapter
from ...ritual.timing import PLANETARY_HOUR_TABLE
from .models import GeoLocation, PlanetaryHourResult

__all__ = ["planetary_hour", "sunrise_sunset", "moonrise_moonset"]



_HAS_SWE = swe is not None
_RISE_FLAGS = (
    (swe.BIT_DISC_CENTER | swe.BIT_NO_REFRACTION | swe.FLG_SWIEPH)
    if _HAS_SWE
    else 0
)
_MOON_FLAGS = _RISE_FLAGS



def _normalize_moment(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


def _ensure_adapter(
    adapter: "SwissEphemerisAdapter | None",
) -> "SwissEphemerisAdapter":
    if _SwissAdapter is None:
        raise RuntimeError(
            "Swiss Ephemeris support is required for rise/transit calculations"
        )
    return adapter or _SwissAdapter.get_default_adapter()



def _next_event(
    adapter: "SwissEphemerisAdapter",
    jd_ut: float,
    event: str,
    location: GeoLocation,
    *,

    body_code: int,
    body_name: str,

) -> float:
    result = adapter.rise_transit(
        jd_ut,
        body_code,
        latitude=location.latitude,
        longitude=location.longitude,
        elevation=location.altitude,
        event=event,

        flags=_RISE_FLAGS,

        body_name=body_name,

    )
    if result.status != 0 or result.julian_day is None:
        label = body_name or "body"
        raise RuntimeError(
            f"Swiss Ephemeris could not compute {label.lower()} {event} for location"
        )
    return result.julian_day



def sunrise_sunset(
    moment: datetime,
    location: GeoLocation,
    *,
    adapter: "SwissEphemerisAdapter | None" = None,
) -> tuple[datetime, datetime, datetime]:
    """Return sunrise, sunset, and next sunrise surrounding ``moment``."""


    adapter = adapter or SwissEphemerisAdapter.get_default_adapter()
    jd = julian_day(moment)
    prev_sunrise_jd = _next_event(
        adapter, jd - 1.0, "rise", location, body_code=swe.SUN, body_name="Sun"
    )
    sunset_jd = _next_event(
        adapter,
        prev_sunrise_jd + 0.01,
        "set",
        location,
        body_code=swe.SUN,
        body_name="Sun",
    )
    next_sunrise_jd = _next_event(
        adapter,
        prev_sunrise_jd + 0.51,
        "rise",
        location,
        body_code=swe.SUN,
        body_name="Sun",
    )
    sunrise_dt = adapter.from_julian_day(prev_sunrise_jd)
    sunset_dt = adapter.from_julian_day(sunset_jd)
    next_sunrise_dt = adapter.from_julian_day(next_sunrise_jd)

    return sunrise_dt, sunset_dt, next_sunrise_dt


def moonrise_moonset(
    moment: datetime,
    location: GeoLocation,
    *,
    adapter: "SwissEphemerisAdapter | None" = None,
) -> tuple[datetime, datetime, datetime]:
    """Return moonrise, moonset, and next moonrise surrounding ``moment``."""

    normalized = _normalize_moment(moment)

    resolved_adapter = _ensure_adapter(adapter)
    jd = _SwissAdapter.julian_day(normalized)
    prev_rise = _next_event(
        resolved_adapter,
        jd - 1.0,
        "rise",
        location,
        body_code=swe.MOON,
        body_name="Moon",
        flags=_MOON_FLAGS,
    )
    set_jd = _next_event(
        resolved_adapter,
        prev_rise + 0.01,
        "set",
        location,
        body_code=swe.MOON,
        body_name="Moon",
        flags=_MOON_FLAGS,
    )
    next_rise = _next_event(
        resolved_adapter,
        prev_rise + 0.51,
        "rise",
        location,
        body_code=swe.MOON,
        body_name="Moon",
        flags=_MOON_FLAGS,
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

def moonrise_moonset(
    moment: datetime,
    location: GeoLocation,
    *,
    adapter: SwissEphemerisAdapter | None = None,
) -> tuple[datetime, datetime, datetime]:
    """Return moonrise, moonset, and next moonrise around ``moment``."""

    adapter = adapter or SwissEphemerisAdapter.get_default_adapter()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    else:
        moment = moment.astimezone(UTC)

    jd = julian_day(moment)
    prev_moonrise_jd = _next_event(
        adapter,
        jd - 1.0,
        "rise",
        location,
        body_code=swe.MOON,
        body_name="Moon",
    )
    moonset_jd = _next_event(
        adapter,
        prev_moonrise_jd + 0.01,
        "set",
        location,
        body_code=swe.MOON,
        body_name="Moon",
    )
    next_moonrise_jd = _next_event(
        adapter,
        prev_moonrise_jd + 0.51,
        "rise",
        location,
        body_code=swe.MOON,
        body_name="Moon",
    )

    return (
        adapter.from_julian_day(prev_moonrise_jd).astimezone(UTC),
        adapter.from_julian_day(moonset_jd).astimezone(UTC),
        adapter.from_julian_day(next_moonrise_jd).astimezone(UTC),
    )

