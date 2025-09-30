"""Sect classification helpers."""

from __future__ import annotations

from datetime import UTC, datetime

import swisseph as swe

from ...ephemeris.swisseph_adapter import SwissEphemerisAdapter
from ...ux.maps.astrocartography import _horizontal_coordinates, _sidereal_time_degrees
from ..traditional.models import GeoLocation, SectInfo

__all__ = ["sect_info"]


def _sun_altitude(moment: datetime, location: GeoLocation, adapter: SwissEphemerisAdapter | None) -> float:
    adapter = adapter or SwissEphemerisAdapter.get_default_adapter()
    jd_ut = adapter.julian_day(moment.astimezone(UTC))
    sun_equatorial = adapter.body_equatorial(jd_ut, swe.SUN)
    lst = _sidereal_time_degrees(jd_ut, location.longitude)
    hour_angle = (lst - sun_equatorial.right_ascension) % 360.0
    _, altitude = _horizontal_coordinates(
        hour_angle_deg=hour_angle,
        decl_deg=sun_equatorial.declination,
        latitude_deg=location.latitude,
    )
    return altitude


def sect_info(moment: datetime, loc: GeoLocation) -> SectInfo:
    """Return sect metadata for the supplied chart moment and location."""

    if moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None:
        raise ValueError("Moment must be timezone-aware")
    altitude = _sun_altitude(moment, loc, None)
    is_day = altitude > 0.0
    luminary = "Sun" if is_day else "Moon"
    benefic = "Jupiter" if is_day else "Venus"
    malefic = "Saturn" if is_day else "Mars"
    return SectInfo(
        is_day=is_day,
        luminary_of_sect=luminary,
        malefic_of_sect=malefic,
        benefic_of_sect=benefic,
        sun_altitude_deg=altitude,
    )
