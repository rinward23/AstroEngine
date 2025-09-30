"""Planetary hour computation utilities."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from ...ephemeris.adapter import ObserverLocation
from ...ritual.timing import PLANETARY_HOUR_TABLE
from ..observational.sun import solar_cycle
from .models import GeoLocation, PlanetaryHourResult

__all__ = ["planetary_hour", "sunrise_sunset"]


def sunrise_sunset(moment: datetime, location: GeoLocation) -> tuple[datetime, datetime, datetime]:
    """Return sunrise, sunset, and next sunrise surrounding ``moment``."""

    observer = ObserverLocation(
        latitude_deg=float(location.latitude),
        longitude_deg=float(location.longitude),
        elevation_m=float(location.altitude),
    )
    return solar_cycle(moment, observer)


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

