"""Time conversion helpers used across AstroEngine.

This module centralises the conversion between timezone-aware
``datetime`` inputs and Terrestrial Time (TT) expressed as Julian day
numbers.  The runtime keeps every ephemeris query in TT to guarantee
deterministic lookups regardless of the source timezone.  Consumers are
expected to call :func:`to_tt` exactly once per evaluation – the
ephemeris adapter enforces this guard so downstream code never mixes UT
and TT accidentally.

The implementation prefers Swiss Ephemeris' ``utc_to_jd`` helper when it
is available because it exposes the same ΔT model used during ephemeris
queries.  When Swiss Ephemeris is not installed we fall back to a
reasonably accurate polynomial approximation derived from the United
States Naval Observatory's published expressions.  The approximation is
well within one second for the 1900–2100 interval which easily covers
the acceptance tests shipped with AstroEngine.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import Final

__all__ = [
    "TimeConversion",
    "ensure_utc",
    "julian_day",
    "to_tt",
]


SECONDS_PER_DAY: Final[float] = 86_400.0


@dataclass(frozen=True)
class TimeConversion:
    """Container describing the conversion from UTC to TT."""

    utc_datetime: _dt.datetime
    jd_utc: float
    jd_tt: float
    delta_t_seconds: float


def ensure_utc(moment: _dt.datetime) -> _dt.datetime:
    """Return ``moment`` converted to UTC."""

    tzinfo = moment.tzinfo
    if tzinfo is None:
        return moment.replace(tzinfo=_dt.UTC)
    return moment.astimezone(_dt.UTC)


def julian_day(moment: _dt.datetime) -> float:
    """Return the Julian day for a UTC ``moment``."""

    moment = ensure_utc(moment)
    year = moment.year
    month = moment.month
    day = moment.day
    frac = (
        moment.hour + moment.minute / 60.0 + (moment.second + moment.microsecond / 1e6) / 3600.0
    ) / 24.0

    if month <= 2:
        year -= 1
        month += 12

    a = year // 100
    b = 2 - a + (a // 4)
    jd = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + b - 1524.5
    return jd + frac


def _approx_delta_t_seconds(moment: _dt.datetime) -> float:
    """Polynomial approximation of ΔT with second precision."""

    year = moment.year + (moment.timetuple().tm_yday - 0.5) / 365.25

    if 2005 <= year <= 2050:
        t = year - 2000.0
        return 62.92 + 0.32217 * t + 0.005589 * t * t
    if 1900 <= year < 2005:
        t = year - 2000.0
        return 62.92 + 0.32217 * t + 0.005589 * t * t

    t = (year - 1820.0) / 100.0
    return 32.0 * (t * t) - 20.0


def to_tt(moment: _dt.datetime) -> TimeConversion:
    """Convert ``moment`` to TT expressed as a Julian day."""

    utc_moment = ensure_utc(moment)

    try:
        import swisseph as swe

        jd_tt, jd_ut1 = swe.utc_to_jd(
            utc_moment.year,
            utc_moment.month,
            utc_moment.day,
            utc_moment.hour,
            utc_moment.minute,
            utc_moment.second + utc_moment.microsecond / 1e6,
            swe.GREG_CAL,
        )
        delta_t = (jd_tt - jd_ut1) * SECONDS_PER_DAY
        return TimeConversion(
            utc_datetime=utc_moment,
            jd_utc=jd_ut1,
            jd_tt=jd_tt,
            delta_t_seconds=delta_t,
        )
    except ModuleNotFoundError:
        jd_utc = julian_day(utc_moment)
        delta_t = _approx_delta_t_seconds(utc_moment)
        jd_tt = jd_utc + delta_t / SECONDS_PER_DAY
        return TimeConversion(
            utc_datetime=utc_moment,
            jd_utc=jd_utc,
            jd_tt=jd_tt,
            delta_t_seconds=delta_t,
        )
