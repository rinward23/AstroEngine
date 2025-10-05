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
from .declinations import DeclinationAspect, declination_aspects, get_declinations
from .returns import aries_ingress_year, lunar_return_datetimes, solar_return_datetime
from .timeline import (
    VoidOfCourseEvent,
    find_eclipses,
    find_lunations,
    find_stations,
    void_of_course_moon,
)

__all__ = [
    # Midpoints & dignities
    "compute_midpoints",
    "get_midpoint_settings",
    "midpoint_longitude",
    "DeclinationAspect",
    "declination_aspects",
    "get_declinations",
    "condition_report",
    "score_accidental",
    "score_essential",
    # Astrocartography
    "AstrocartographyResult",
    "MapLine",
    "compute_astrocartography_lines",
    # Declinations
    "DeclinationAspect",
    "declination_aspects",
    "get_declinations",
    # Returns & ingresses
    "ReturnComputationError",
    "aries_ingress_year",
    "lunar_return_datetimes",
    "solar_return_datetime",
    # Timeline helpers
    "VoidOfCourseEvent",
    "find_eclipses",
    "find_lunations",
    "find_stations",
    "void_of_course_moon",
]


def load_optional_analysis_utilities() -> None:
    """Eagerly import helpers that rely on optional dependencies.

    The re-exports above are sufficient for most use cases, but some callers may
    still prefer to explicitly import the submodules that depend on optional
    extras (for example when wiring routers at startup).  Import errors due to
    missing extras are swallowed so that environments without those packages can
    continue operating with the available feature set.
    """

    for module_name in ("astrocartography", "declinations", "timeline", "returns"):
        try:
            __import__(f"{__name__}.{module_name}")
        except ModuleNotFoundError:
            # Optional dependency not installed – callers can inspect availability
            # when they actually invoke the functionality.
            continue
