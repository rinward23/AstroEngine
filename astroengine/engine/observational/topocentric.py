"""Topocentric coordinate transforms and refraction utilities."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime

from ...core.stars_plus.geometry import mean_obliquity_deg
from ...core.time import julian_day
from ...ephemeris.adapter import EphemerisAdapter, EphemerisSample, ObserverLocation
from .earth import Vec3, ecef_from_geodetic, gcrs_from_ecef


@dataclass(frozen=True)
class MetConditions:
    """Atmospheric conditions used when modelling refraction."""

    temperature_c: float = 10.0
    pressure_hpa: float = 1010.0


@dataclass(frozen=True)
class TopocentricEquatorial:
    """Right ascension / declination triple referenced to the observer."""

    right_ascension_deg: float
    declination_deg: float
    distance_au: float


@dataclass(frozen=True)
class TopocentricEcliptic:
    """Ecliptic longitude / latitude triple referenced to the observer."""

    longitude_deg: float
    latitude_deg: float
    distance_au: float


@dataclass(frozen=True)
class HorizontalCoordinates:
    """Alt/Az coordinates measured from the local horizon."""

    altitude_deg: float
    azimuth_deg: float


def _utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


def _geocentric_vector(sample: EphemerisSample) -> Vec3:
    ra_rad = math.radians(sample.right_ascension)
    dec_rad = math.radians(sample.declination)
    r = sample.distance
    cos_dec = math.cos(dec_rad)
    return Vec3(
        r * cos_dec * math.cos(ra_rad),
        r * cos_dec * math.sin(ra_rad),
        r * math.sin(dec_rad),
    )


def _observer_vector(observer: ObserverLocation, moment: datetime) -> Vec3:
    ecef = ecef_from_geodetic(
        observer.latitude_deg, observer.longitude_deg, observer.elevation_m
    )
    return gcrs_from_ecef(ecef, moment)


def _rectangular_to_equatorial(vec: Vec3) -> TopocentricEquatorial:
    r = vec.magnitude()
    ra = math.degrees(math.atan2(vec.y, vec.x)) % 360.0
    dec = math.degrees(math.asin(vec.z / r)) if r != 0 else 0.0
    return TopocentricEquatorial(ra, dec, r)


def topocentric_equatorial(
    adapter: EphemerisAdapter,
    body: int,
    moment: datetime,
    observer: ObserverLocation,
) -> TopocentricEquatorial:
    """Return topocentric apparent equatorial coordinates."""

    geo_sample = adapter.sample(body, moment)
    geo_vec = _geocentric_vector(geo_sample)
    obs_vec = _observer_vector(observer, moment)
    topo_vec = geo_vec.minus(obs_vec)
    return _rectangular_to_equatorial(topo_vec)


def topocentric_ecliptic(
    adapter: EphemerisAdapter,
    body: int,
    moment: datetime,
    observer: ObserverLocation,
) -> TopocentricEcliptic:
    """Return topocentric apparent ecliptic coordinates."""

    topo_equ = topocentric_equatorial(adapter, body, moment, observer)
    epsilon = mean_obliquity_deg(_utc(moment))
    ra = math.radians(topo_equ.right_ascension_deg)
    dec = math.radians(topo_equ.declination_deg)
    eps = math.radians(epsilon)
    sin_beta = math.sin(dec) * math.cos(eps) - math.cos(dec) * math.sin(eps) * math.sin(ra)
    beta = math.degrees(math.asin(sin_beta))
    y = math.sin(ra) * math.cos(eps) + math.tan(dec) * math.sin(eps)
    x = math.cos(ra)
    lam = math.degrees(math.atan2(y, x)) % 360.0
    return TopocentricEcliptic(lam, beta, topo_equ.distance_au)


def refraction_saemundsson(
    altitude_deg: float, temperature_c: float, pressure_hpa: float
) -> float:
    """Return refraction in arcminutes at the apparent altitude ``altitude_deg``."""

    if altitude_deg < -1.0 or altitude_deg > 90.0:
        return 0.0
    denom = math.tan(math.radians(altitude_deg + 10.3 / (altitude_deg + 5.11)))
    if denom == 0:
        return 0.0
    R = 1.02 / denom
    R *= (pressure_hpa / 1010.0) * (283.0 / (273.0 + temperature_c))
    return R


def horizontal_from_equatorial(
    ra_deg: float,
    dec_deg: float,
    moment: datetime,
    observer: ObserverLocation,
    *,
    refraction: bool = True,
    met: MetConditions | None = None,
    horizon_dip_deg: float = 0.0,
) -> HorizontalCoordinates:
    """Convert equatorial coordinates to horizontal Alt/Az."""

    met = met or MetConditions()
    utc_moment = _utc(moment)
    phi = math.radians(observer.latitude_deg)
    lst_deg = _local_sidereal_deg(utc_moment, observer.longitude_deg)
    H = math.radians((lst_deg - ra_deg + 540.0) % 360.0 - 180.0)
    dec_rad = math.radians(dec_deg)
    sin_alt = (
        math.sin(dec_rad) * math.sin(phi)
        + math.cos(dec_rad) * math.cos(phi) * math.cos(H)
    )
    sin_alt = max(-1.0, min(1.0, sin_alt))
    alt = math.degrees(math.asin(sin_alt))
    cos_alt = math.cos(math.radians(alt))
    if abs(cos_alt) < 1e-12:
        az = 0.0
    else:
        sin_az = -math.sin(H) * math.cos(dec_rad) / cos_alt
        cos_az = (
            math.sin(dec_rad) - math.sin(math.radians(alt)) * math.sin(phi)
        ) / (math.cos(math.radians(alt)) * math.cos(phi))
        az = math.degrees(math.atan2(sin_az, cos_az)) % 360.0

    apparent_alt = alt
    if refraction:
        correction = refraction_saemundsson(
            alt, met.temperature_c, met.pressure_hpa
        ) / 60.0
        apparent_alt += correction
    apparent_alt += horizon_dip_deg
    return HorizontalCoordinates(apparent_alt, az)


def _local_sidereal_deg(moment: datetime, lon_deg: float) -> float:
    jd = julian_day(moment)
    T = (jd - 2451545.0) / 36525.0
    gmst = (
        280.46061837
        + 360.98564736629 * (jd - 2451545.0)
        + 0.000387933 * T * T
        - (T ** 3) / 38710000.0
    )
    lst = (gmst + lon_deg) % 360.0
    return lst


__all__ = [
    "HorizontalCoordinates",
    "MetConditions",
    "TopocentricEcliptic",
    "TopocentricEquatorial",
    "horizontal_from_equatorial",
    "refraction_saemundsson",
    "topocentric_ecliptic",
    "topocentric_equatorial",
]
