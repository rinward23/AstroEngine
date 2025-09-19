"""Swiss Ephemeris-backed fixed star helpers."""

from __future__ import annotations

import datetime as _dt
from typing import Tuple

try:  # pragma: no cover - optional dependency
    import swisseph as swe
except ModuleNotFoundError:  # pragma: no cover
    swe = None  # type: ignore


def _parse_iso_to_datetime(iso_utc: str) -> _dt.datetime:
    moment = _dt.datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
    if moment.tzinfo is None:
        return moment.replace(tzinfo=_dt.timezone.utc)
    return moment.astimezone(_dt.timezone.utc)


def _datetime_to_jd_ut(moment: _dt.datetime) -> float:
    if swe is None:  # pragma: no cover - guarded by caller
        raise ImportError("pyswisseph not installed")
    utc = moment.astimezone(_dt.timezone.utc)
    hour = utc.hour + utc.minute / 60.0 + (utc.second + utc.microsecond / 1e6) / 3600.0
    return swe.julday(utc.year, utc.month, utc.day, hour)


def fixstar_lonlat(name: str, iso_utc: str) -> Tuple[float, float]:
    """Return ecliptic longitude/latitude for ``name`` at ``iso_utc`` using Swiss Ephemeris."""

    if swe is None:
        raise ImportError("pyswisseph not installed")
    moment = _parse_iso_to_datetime(iso_utc)
    jd_ut = _datetime_to_jd_ut(moment)
    values, _ = swe.fixstar2_ut(name, jd_ut)
    lon = float(values[0] % 360.0)
    lat = float(values[1])
    return lon, lat


__all__ = ["fixstar_lonlat"]
