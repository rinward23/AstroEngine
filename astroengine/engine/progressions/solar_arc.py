"""Solar arc direction helpers."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Literal, Sequence

from ...core.angles import normalize_degrees
from ...ephemeris.adapter import EphemerisAdapter
from ...providers.swisseph_adapter import SE_SUN

__all__ = [
    "AscMc",
    "GeoLocation",
    "LonLat",
    "apply_solar_arc_longitude",
    "compute_arc_secondary_sun",
    "rotate_angles",
]


@dataclass(frozen=True)
class LonLat:
    """Simple container describing an ecliptic point."""

    longitude: float
    latitude: float = 0.0


@dataclass(frozen=True)
class AscMc:
    """Ascendant/MC pair used during angular rotation."""

    ascendant: float
    midheaven: float


@dataclass(frozen=True)
class GeoLocation:
    """Geographic location used for MC rotation."""

    latitude_deg: float
    longitude_deg: float


def compute_arc_secondary_sun(
    ephem: EphemerisAdapter, t0: object, tP: object
) -> float:
    """Return the solar arc derived from the secondary progressed Sun."""

    natal = ephem.sample(SE_SUN, t0)
    progressed = ephem.sample(SE_SUN, tP)
    arc = normalize_degrees(progressed.longitude - natal.longitude)
    return arc


def apply_solar_arc_longitude(points: Sequence[LonLat], arc_deg: float) -> list[LonLat]:
    """Return ``points`` shifted by ``arc_deg`` along the ecliptic."""

    shifted: list[LonLat] = []
    for point in points:
        lon = normalize_degrees(point.longitude + arc_deg)
        shifted.append(LonLat(longitude=lon, latitude=point.latitude))
    return shifted


def rotate_angles(
    mode: Literal["LongitudeShift", "MCRotation"],
    asc_mc: AscMc,
    arc_deg: float,
    *,
    loc: GeoLocation | None = None,
    obliquity_deg: float | None = None,
) -> AscMc:
    """Rotate ``asc_mc`` by ``arc_deg`` using the requested ``mode``."""

    arc = normalize_degrees(arc_deg)
    if mode == "LongitudeShift":
        asc = normalize_degrees(asc_mc.ascendant + arc)
        mc = normalize_degrees(asc_mc.midheaven + arc)
        return AscMc(ascendant=asc, midheaven=mc)

    if mode != "MCRotation":  # pragma: no cover - defensive
        raise ValueError(f"unsupported solar arc rotation mode: {mode}")

    if loc is None or obliquity_deg is None:
        raise ValueError("MCRotation mode requires location and obliquity")

    mc = normalize_degrees(asc_mc.midheaven + arc)
    epsilon = math.radians(obliquity_deg)
    phi = math.radians(loc.latitude_deg)
    mc_rad = math.radians(mc)

    numerator = math.sin(mc_rad) * math.cos(epsilon) - math.tan(phi) * math.sin(
        epsilon
    )
    denominator = math.cos(mc_rad)
    asc = math.degrees(math.atan2(numerator, denominator))
    asc = normalize_degrees(asc)
    return AscMc(ascendant=asc, midheaven=mc)
