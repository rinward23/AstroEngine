"""Declination and antiscia helpers used by detectors."""

from __future__ import annotations

import math

__all__ = [
    "OBLIQUITY_DEG",
    "ecl_to_dec",
    "is_parallel",
    "is_contraparallel",
    "antiscia_lon",
    "contra_antiscia_lon",
]

OBLIQUITY_DEG = 23.4367  # mean obliquity of the ecliptic (approx J2000)
OBLIQUITY_RAD = math.radians(OBLIQUITY_DEG)


def ecl_to_dec(lon_deg: float) -> float:
    """Convert ecliptic longitude (λ) at latitude=0° into declination (δ)."""

    lon_rad = math.radians(lon_deg % 360.0)
    sin_dec = math.sin(lon_rad) * math.sin(OBLIQUITY_RAD)
    return math.degrees(math.asin(max(-1.0, min(1.0, sin_dec))))


def is_parallel(dec1: float, dec2: float, orb: float) -> bool:
    return abs(dec1 - dec2) <= abs(orb)


def is_contraparallel(dec1: float, dec2: float, orb: float) -> bool:
    return abs(dec1 + dec2) <= abs(orb)


def antiscia_lon(lon_deg: float) -> float:
    return (180.0 - lon_deg) % 360.0


def contra_antiscia_lon(lon_deg: float) -> float:
    return (360.0 - lon_deg) % 360.0
