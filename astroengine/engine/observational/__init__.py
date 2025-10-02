"""Topocentric observational geometry utilities."""

from __future__ import annotations

from ...ephemeris.adapter import EphemerisAdapter, EphemerisSample, ObserverLocation

from .earth import ecef_from_geodetic, gcrs_from_ecef
from .topocentric import (
    HorizontalCoordinates,
    MetConditions,
    TopocentricEcliptic,
    TopocentricEquatorial,
    horizontal_from_equatorial,
    refraction_saemundsson,
    topocentric_ecliptic,
    topocentric_equatorial,
)
from .events import EventOptions, rise_set_times, transit_time
from .sun import solar_cycle, solar_cycle_for_location
from .windows import (
    HeliacalProfile,
    VisibilityConstraints,
    VisibilityWindow,
    heliacal_candidates,
    visibility_windows,
)
from .diagrams import AltAzDiagram, render_altaz_diagram

__all__ = [
    "AltAzDiagram",
    "EphemerisAdapter",
    "EphemerisSample",
    "EventOptions",
    "HeliacalProfile",
    "HorizontalCoordinates",
    "MetConditions",
    "ObserverLocation",
    "TopocentricEcliptic",
    "TopocentricEquatorial",
    "VisibilityConstraints",
    "VisibilityWindow",
    "ecef_from_geodetic",
    "gcrs_from_ecef",
    "heliacal_candidates",
    "horizontal_from_equatorial",
    "refraction_saemundsson",
    "render_altaz_diagram",
    "rise_set_times",
    "solar_cycle",
    "solar_cycle_for_location",
    "topocentric_ecliptic",
    "topocentric_equatorial",
    "transit_time",
    "visibility_windows",
]
