"""Declination and antiscia helpers used by detectors."""

from __future__ import annotations

import math

__all__ = [
    "ANTISCIA_AXIS_CENTERS",
    "DEFAULT_ANTISCIA_AXIS",
    "OBLIQUITY_DEG",
    "antiscia_lon",
    "available_antiscia_axes",
    "contra_antiscia_lon",
    "ecl_to_dec",
    "is_contraparallel",
    "is_parallel",
]

OBLIQUITY_DEG = 23.4367  # mean obliquity of the ecliptic (approx J2000)
OBLIQUITY_RAD = math.radians(OBLIQUITY_DEG)

ANTISCIA_AXIS_CENTERS: dict[str, float] = {
    "cancer_capricorn": 90.0,
    "capricorn_cancer": 90.0,
    "solstitial": 90.0,
    "aries_libra": 0.0,
    "libra_aries": 0.0,
    "equinoctial": 0.0,
}
"""Mapping of supported antiscia axes to their central longitude in degrees."""

DEFAULT_ANTISCIA_AXIS = "cancer_capricorn"


def available_antiscia_axes() -> tuple[str, ...]:
    """Return the tuple of supported antiscia axis identifiers."""

    return tuple(sorted(set(ANTISCIA_AXIS_CENTERS)))


def ecl_to_dec(lon_deg: float) -> float:
    """Convert ecliptic longitude (λ) at latitude=0° into declination (δ)."""

    lon_rad = math.radians(lon_deg % 360.0)
    sin_dec = math.sin(lon_rad) * math.sin(OBLIQUITY_RAD)
    return math.degrees(math.asin(max(-1.0, min(1.0, sin_dec))))


def is_parallel(
    dec1: float, dec2: float, orb: float | None = None, *, tol_deg: float | None = None
) -> bool:
    threshold = tol_deg if tol_deg is not None else orb
    if threshold is None:
        raise TypeError("is_parallel requires an orb or tol_deg value")
    return abs(dec1 - dec2) <= abs(threshold)


def is_contraparallel(
    dec1: float, dec2: float, orb: float | None = None, *, tol_deg: float | None = None
) -> bool:
    threshold = tol_deg if tol_deg is not None else orb
    if threshold is None:
        raise TypeError("is_contraparallel requires an orb or tol_deg value")
    return abs(dec1 + dec2) <= abs(threshold)


def _axis_center(axis: str | None) -> float:
    if not axis:
        axis = DEFAULT_ANTISCIA_AXIS
    key = axis.lower()
    try:
        return ANTISCIA_AXIS_CENTERS[key]
    except KeyError as exc:  # pragma: no cover - defensive guard
        raise ValueError(f"Unsupported antiscia axis: {axis}") from exc


def antiscia_lon(lon_deg: float, axis: str = DEFAULT_ANTISCIA_AXIS) -> float:
    """Return the antiscia mirror of ``lon_deg`` across the supplied axis."""

    center = _axis_center(axis)
    return (2.0 * center - lon_deg) % 360.0


def contra_antiscia_lon(lon_deg: float, axis: str = DEFAULT_ANTISCIA_AXIS) -> float:
    """Return the contra-antiscia mirror of ``lon_deg`` across the supplied axis."""

    # Contra-antiscia mirrors lie 90° away from the antiscia axis.
    center = (_axis_center(axis) + 90.0) % 360.0
    return (2.0 * center - lon_deg) % 360.0
