"""Composite and Davison chart helpers.

This module keeps the math utilities pure so they can be reused by API or UI
layers without extra dependencies. All functions assume degrees for angles and
UTC-aware datetimes when timestamps are provided.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

PositionProvider = Callable[[datetime], dict[str, float]]


# --------------------------- Angle utils -----------------------------------

def norm360(value: float) -> float:
    """Normalize an angle to the ``[0, 360)`` range."""

    v = float(value) % 360.0
    return v + 360.0 if v < 0 else v


def delta_short(a: float, b: float) -> float:
    """Signed smallest angular difference ``b - a`` in degrees in ``(-180, 180]``."""

    d = (float(b) - float(a) + 540.0) % 360.0 - 180.0
    # When ``a`` and ``b`` are exactly opposite, the modulo arithmetic produces
    # ``-180``. For midpoint work we prefer the positive orientation so the
    # midpoint lands halfway along the +180° arc.
    if d <= -180.0:
        return 180.0
    return d


def midpoint_angle(a: float, b: float) -> float:
    """Circular midpoint along the shortest arc between ``a`` and ``b``."""

    a = float(a)
    d = delta_short(a, b)  # ``b`` relative to ``a``
    return norm360(a + 0.5 * d)


# --------------------------- Composite positions ---------------------------

def composite_positions(
    pos_a: dict[str, float],
    pos_b: dict[str, float],
    bodies: Iterable[str] | None = None,
) -> dict[str, float]:
    """Return midpoint longitudes for bodies shared between ``pos_a`` and ``pos_b``.

    Parameters
    ----------
    pos_a, pos_b:
        Mappings from body name to ecliptic longitude in degrees.
    bodies:
        Optional iterable restricting which bodies to consider. Only entries
        present in both position dictionaries are included in the result.
    """

    if bodies is None:
        common = set(pos_a.keys()) & set(pos_b.keys())
    else:
        common = {key for key in bodies if key in pos_a and key in pos_b}

    out: dict[str, float] = {}
    for key in sorted(common):
        out[key] = midpoint_angle(pos_a[key], pos_b[key])
    return out


# --------------------------- Davison midpoints ------------------------------


@dataclass(frozen=True)
class Geo:
    """Simple container for geographic latitude and longitude in degrees."""

    lat_deg: float
    lon_deg_east: float


def _to_vec(lat_deg: float, lon_deg_east: float) -> tuple[float, float, float]:
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg_east)
    x = math.cos(lat) * math.cos(lon)
    y = math.cos(lat) * math.sin(lon)
    z = math.sin(lat)
    return x, y, z


def _from_vec(x: float, y: float, z: float) -> tuple[float, float]:
    hyp = math.hypot(x, y)
    lat = math.degrees(math.atan2(z, hyp))
    lon = math.degrees(math.atan2(y, x))
    return lat, lon


def spherical_midpoint(lat1: float, lon1: float, lat2: float, lon2: float) -> tuple[float, float]:
    """Return the great-circle midpoint on the unit sphere."""

    x1, y1, z1 = _to_vec(lat1, lon1)
    x2, y2, z2 = _to_vec(lat2, lon2)
    xm, ym, zm = (x1 + x2) / 2.0, (y1 + y2) / 2.0, (z1 + z2) / 2.0

    if xm == 0.0 and ym == 0.0 and zm == 0.0:
        # Antipodal pair (or floating point degenerate) falls back to linear mean.
        return (lat1 + lat2) / 2.0, (lon1 + lon2) / 2.0

    return _from_vec(xm, ym, zm)


def time_midpoint_utc(dt_a: datetime, dt_b: datetime) -> datetime:
    """Return the midpoint between ``dt_a`` and ``dt_b`` expressed in UTC."""

    a = dt_a.astimezone(UTC) if dt_a.tzinfo else dt_a.replace(tzinfo=UTC)
    b = dt_b.astimezone(UTC) if dt_b.tzinfo else dt_b.replace(tzinfo=UTC)
    t = (a.timestamp() + b.timestamp()) / 2.0
    return datetime.fromtimestamp(t, tz=UTC)


def davison_midpoints(
    dt_a: datetime,
    loc_a: Geo,
    dt_b: datetime,
    loc_b: Geo,
) -> tuple[datetime, float, float]:
    """Return the Davison midpoint timestamp, latitude, and longitude."""

    mid_dt = time_midpoint_utc(dt_a, dt_b)
    mid_lat, mid_lon = spherical_midpoint(
        loc_a.lat_deg,
        loc_a.lon_deg_east,
        loc_b.lat_deg,
        loc_b.lon_deg_east,
    )
    return mid_dt, mid_lat, mid_lon


def davison_positions(
    provider: PositionProvider,
    dt_a: datetime,
    loc_a: Geo,
    dt_b: datetime,
    loc_b: Geo,
    bodies: Iterable[str] | None = None,
) -> dict[str, float]:
    """Return body longitudes for the Davison chart at the time midpoint."""

    mid_dt, _, _ = davison_midpoints(dt_a, loc_a, dt_b, loc_b)
    positions = provider(mid_dt)
    if bodies is None:
        return dict(positions)
    return {key: positions[key] for key in bodies if key in positions}


__all__ = [
    "Geo",
    "PositionProvider",
    "composite_positions",
    "davison_midpoints",
    "davison_positions",
    "delta_short",
    "midpoint_angle",
    "norm360",
    "spherical_midpoint",
    "time_midpoint_utc",
]
