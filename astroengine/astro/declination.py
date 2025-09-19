"""Declination and mirror helpers."""

from __future__ import annotations

import math

from ..utils.angles import norm360

__all__ = [
    "OBLIQUITY_DEG",
    "ecl_to_dec",
    "is_parallel",
    "is_contraparallel",
    "antiscia_lon",
    "contra_antiscia_lon",
]

OBLIQUITY_DEG = 23.4392911


def ecl_to_dec(lon_deg: float, lat_deg: float = 0.0) -> float:
    """Convert ecliptic longitude/latitude to declination in degrees.

    Uses mean obliquity of the ecliptic (`OBLIQUITY_DEG`). Latitude defaults to 0°
    which is sufficient for coarse scans where only longitude is supplied.
    """
    lam = math.radians(norm360(lon_deg))
    beta = math.radians(lat_deg)
    eps = math.radians(OBLIQUITY_DEG)
    sin_dec = math.sin(beta) * math.cos(eps) + math.cos(beta) * math.sin(eps) * math.sin(lam)
    return math.degrees(math.asin(max(-1.0, min(1.0, sin_dec))))


def is_parallel(dec_a: float, dec_b: float, orb_deg: float) -> bool:
    return abs(dec_a - dec_b) <= abs(orb_deg)


def is_contraparallel(dec_a: float, dec_b: float, orb_deg: float) -> bool:
    return abs(dec_a + dec_b) <= abs(orb_deg)


def antiscia_lon(lon_deg: float) -> float:
    return norm360(180.0 - lon_deg)


def contra_antiscia_lon(lon_deg: float) -> float:
    return norm360(-lon_deg)
