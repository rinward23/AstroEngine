"""Fixed-star utilities for AstroEngine."""

from __future__ import annotations

from .aspects import find_star_aspects, star_longitudes
from .catalog import Star, load_catalog
from .geometry import (
    approximate_transit_times,
    gmst_deg,
    lst_deg,
    mean_obliquity_deg,
    norm360,
    radec_to_ecliptic_lon_deg,
    rise_set_hour_angle_deg,
)
from .parans import Location, ParanEvent, ParanPair, detect_parans

__all__ = [
    "Star",
    "load_catalog",
    "star_longitudes",
    "find_star_aspects",
    "Location",
    "ParanPair",
    "ParanEvent",
    "detect_parans",
    "approximate_transit_times",
    "gmst_deg",
    "lst_deg",
    "mean_obliquity_deg",
    "norm360",
    "radec_to_ecliptic_lon_deg",
    "rise_set_hour_angle_deg",
]
