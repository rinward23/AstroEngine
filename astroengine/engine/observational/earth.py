"""Earth orientation helpers for topocentric calculations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import math

from ...core.time import julian_day

_AU_METERS = 149_597_870_700.0
_WGS84_A = 6_378_137.0  # semi-major axis in meters
_WGS84_F = 1 / 298.257_223_563  # flattening
_WGS84_E2 = _WGS84_F * (2 - _WGS84_F)


@dataclass(frozen=True)
class Vec3:
    """Simple 3D vector container."""

    x: float
    y: float
    z: float

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def scaled(self, factor: float) -> "Vec3":
        return Vec3(self.x * factor, self.y * factor, self.z * factor)

    def minus(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def magnitude(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)


def ecef_from_geodetic(lat_deg: float, lon_deg: float, height_m: float = 0.0) -> Vec3:
    """Return the WGS-84 Earth-fixed vector for a geodetic observer."""

    lat_rad = math.radians(lat_deg)
    lon_rad = math.radians(lon_deg)
    sin_lat = math.sin(lat_rad)
    cos_lat = math.cos(lat_rad)
    sin_lon = math.sin(lon_rad)
    cos_lon = math.cos(lon_rad)

    N = _WGS84_A / math.sqrt(1.0 - _WGS84_E2 * sin_lat * sin_lat)
    x = (N + height_m) * cos_lat * cos_lon
    y = (N + height_m) * cos_lat * sin_lon
    z = (N * (1 - _WGS84_E2) + height_m) * sin_lat
    return Vec3(x, y, z)


def _era_rad(moment: datetime) -> float:
    """Approximate Earth rotation angle in radians."""

    utc = moment.astimezone(UTC) if moment.tzinfo else moment.replace(tzinfo=UTC)
    jd_ut1 = julian_day(utc)
    days = jd_ut1 - 2451545.0
    fraction = 0.7790572732640 + 1.00273781191135448 * days
    theta = (fraction % 1.0) * 2.0 * math.pi
    return theta


def gcrs_from_ecef(ecef: Vec3, moment: datetime) -> Vec3:
    """Rotate an ECEF vector into the inertial GCRS frame (ignoring polar motion)."""

    theta = _era_rad(moment)
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    x = ecef.x * cos_t - ecef.y * sin_t
    y = ecef.x * sin_t + ecef.y * cos_t
    z = ecef.z
    return Vec3(x / _AU_METERS, y / _AU_METERS, z / _AU_METERS)


__all__ = ["Vec3", "ecef_from_geodetic", "gcrs_from_ecef"]
