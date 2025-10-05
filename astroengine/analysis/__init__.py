"""Analysis utilities exposed via :mod:`astroengine.analysis`."""

from __future__ import annotations

from .astrocartography import (
    AstrocartographyResult,
    MapLine,
    compute_astrocartography_lines,
)
from .declinations import DeclinationAspect, declination_aspects, get_declinations
from .dignities import condition_report, score_accidental, score_essential
from .midpoints import compute_midpoints, get_midpoint_settings, midpoint_longitude
from .returns import aries_ingress_year, lunar_return_datetimes, solar_return_datetime
from .timeline import (
    VoidOfCourseEvent,
    find_eclipses,
    find_lunations,
    find_stations,
    void_of_course_moon,
)

__all__ = [
    "AstrocartographyResult",
    "MapLine",
    "compute_astrocartography_lines",
    "DeclinationAspect",
    "declination_aspects",
    "get_declinations",
    "compute_midpoints",
    "get_midpoint_settings",
    "midpoint_longitude",
    "score_essential",
    "score_accidental",
    "condition_report",
    "aries_ingress_year",
    "lunar_return_datetimes",
    "solar_return_datetime",
    "find_lunations",
    "find_eclipses",
    "find_stations",
    "void_of_course_moon",
    "VoidOfCourseEvent",
]
