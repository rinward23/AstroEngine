"""Sect determination helpers for Arabic Lots evaluation."""

from __future__ import annotations

import datetime as _dt
import math
from dataclasses import dataclass

__all__ = ["GeoLocation", "is_day"]


@dataclass(frozen=True)
class GeoLocation:
    """Simple latitude/longitude container used for sect checks."""

    latitude: float
    longitude: float
    elevation: float = 0.0


def _to_utc(moment: _dt.datetime) -> _dt.datetime:
    if moment.tzinfo is None:
        raise ValueError("datetime must be timezone-aware for sect determination")
    return moment.astimezone(_dt.UTC)


def _julian_day(moment: _dt.datetime) -> float:
    utc = _to_utc(moment)
    year = utc.year
    month = utc.month
    day = utc.day + (utc.hour + utc.minute / 60.0 + utc.second / 3600.0) / 24.0
    if month <= 2:
        year -= 1
        month += 12
    a = math.floor(year / 100)
    b = 2 - a + math.floor(a / 4)
    jd = math.floor(365.25 * (year + 4716))
    jd += math.floor(30.6001 * (month + 1))
    jd += day + b - 1524.5
    return jd


def _solar_declination(jd: float) -> float:
    t = (jd - 2451545.0) / 36525.0
    mean_long = math.radians((280.46646 + 36000.76983 * t) % 360.0)
    mean_anom = math.radians((357.52911 + 35999.05029 * t) % 360.0)
    ecliptic_long = mean_long + math.radians(1.914602 - 0.004817 * t) * math.sin(mean_anom)
    ecliptic_long += math.radians(0.019993 - 0.000101 * t) * math.sin(2 * mean_anom)
    obliquity = math.radians(23.439291 - 0.0130042 * t)
    return math.asin(math.sin(obliquity) * math.sin(ecliptic_long))


def _equation_of_time(jd: float) -> float:
    t = (jd - 2451545.0) / 36525.0
    epsilon = math.radians(23.439291 - 0.0130042 * t)
    l0 = math.radians((280.46646 + 36000.76983 * t) % 360.0)
    e = 0.016708634 - 0.000042037 * t
    m = math.radians((357.52911 + 35999.05029 * t) % 360.0)
    y = math.tan(epsilon / 2.0) ** 2
    sin2l0 = math.sin(2 * l0)
    sinm = math.sin(m)
    cos2l0 = math.cos(2 * l0)
    sin4l0 = math.sin(4 * l0)
    sin2m = math.sin(2 * m)
    return (
        y * sin2l0
        - 2 * e * sinm
        + 4 * e * y * sinm * cos2l0
        - 0.5 * y * y * sin4l0
        - 1.25 * e * e * sin2m
    ) * (180.0 / math.pi) * 4.0


def _solar_altitude(moment: _dt.datetime, location: GeoLocation) -> float:
    jd = _julian_day(moment)
    decl = _solar_declination(jd)
    eq_time = _equation_of_time(jd)
    utc = _to_utc(moment)
    minutes = utc.hour * 60 + utc.minute + utc.second / 60.0
    true_solar_time = (minutes + eq_time + 4 * location.longitude) % 1440
    hour_angle = true_solar_time / 4.0 - 180.0
    if hour_angle < -180.0:
        hour_angle += 360.0
    ha_rad = math.radians(hour_angle)
    lat_rad = math.radians(location.latitude)
    sin_alt = math.sin(lat_rad) * math.sin(decl) + math.cos(lat_rad) * math.cos(decl) * math.cos(ha_rad)
    sin_alt = max(-1.0, min(1.0, sin_alt))
    return math.degrees(math.asin(sin_alt))


def is_day(
    moment: _dt.datetime,
    location: GeoLocation,
    *,
    sun_altitude: float | None = None,
) -> bool:
    """Return ``True`` when the chart is diurnal at ``moment`` and ``location``."""

    if sun_altitude is not None:
        return sun_altitude > 0.0
    altitude = _solar_altitude(moment, location)
    return altitude > 0.0
