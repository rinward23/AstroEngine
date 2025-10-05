"""Locational mapping helpers built on Swiss ephemeris data."""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

from astroengine.analysis.astrocartography import (
    MapLine,
    compute_astrocartography_lines,
)
from astroengine.ephemeris import SwissEphemerisAdapter

try:  # pragma: no cover - optional dependency guard
    import swisseph as swe
except Exception:  # pragma: no cover - exercised when locational extra missing
    swe = None  # type: ignore[assignment]

__all__ = [
    "LocalSpaceVector",
    "MapLine",
    "astrocartography_lines",
    "local_space_vectors",
]

_DEFAULT_BODIES: tuple[str, ...] = (
    "sun",
    "moon",
    "mercury",
    "venus",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
    "pluto",
)

_BODY_RESOLVERS: dict[str, str] = {
    "sun": "SUN",
    "moon": "MOON",
    "mercury": "MERCURY",
    "venus": "VENUS",
    "mars": "MARS",
    "jupiter": "JUPITER",
    "saturn": "SATURN",
    "uranus": "URANUS",
    "neptune": "NEPTUNE",
    "pluto": "PLUTO",
    "chiron": "CHIRON",
    "ceres": "CERES",
    "pallas": "PALLAS",
    "juno": "JUNO",
    "vesta": "VESTA",
}


@dataclass(frozen=True)
class LocalSpaceVector:
    """Azimuth/altitude vector for a body from a specific location."""

    body: str
    azimuth_deg: float
    altitude_deg: float
    metadata: dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "body": self.body,
            "azimuth_deg": self.azimuth_deg,
            "altitude_deg": self.altitude_deg,
            "metadata": dict(self.metadata),
        }


def _require_swisseph() -> None:
    if swe is None:  # pragma: no cover - dependency guard
        raise RuntimeError(
            "Astrocartography helpers require pyswisseph. Install AstroEngine with "
            "the 'locational' extra to enable maps."
        )


def _resolve_body_code(name: str) -> int:
    resolver = _BODY_RESOLVERS.get(name.lower())
    if resolver is None:
        raise KeyError(f"Unsupported body for locational maps: {name}")
    _require_swisseph()
    code = getattr(swe, resolver, None)
    if code is None:
        raise KeyError(f"Swiss Ephemeris does not expose constant '{resolver}'")
    return int(code)


def _moment_to_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


def astrocartography_lines(
    moment: datetime,
    *,
    bodies: Sequence[str] | None = None,
    adapter: SwissEphemerisAdapter | None = None,
    lat_step: float = 1.5,
) -> list[MapLine]:
    """Return astrocartography lines for ``moment``."""

    result = compute_astrocartography_lines(
        moment,
        bodies=bodies or _DEFAULT_BODIES,
        adapter=adapter,
        lat_step=lat_step,
        simplify_tolerance=0.0,
        show_parans=False,
    )
    return list(result.lines)


def _sidereal_time_degrees(jd_ut: float, longitude: float) -> float:
    gst_hours = swe.sidtime(jd_ut)
    return (gst_hours * 15.0 + longitude) % 360.0


def _horizontal_coordinates(
    hour_angle_deg: float, decl_deg: float, latitude_deg: float
) -> tuple[float, float]:
    hour_angle = math.radians(hour_angle_deg)
    delta = math.radians(decl_deg)
    phi = math.radians(latitude_deg)
    sin_alt = math.sin(delta) * math.sin(phi) + math.cos(delta) * math.cos(phi) * math.cos(
        hour_angle
    )
    sin_alt = max(-1.0, min(1.0, sin_alt))
    alt = math.degrees(math.asin(sin_alt))
    cos_az_numerator = math.sin(delta) - math.sin(math.radians(alt)) * math.sin(phi)
    cos_az_denominator = math.cos(math.radians(alt)) * math.cos(phi)
    if abs(cos_az_denominator) < 1e-6:
        az = 0.0
    else:
        cos_az = max(-1.0, min(1.0, cos_az_numerator / cos_az_denominator))
        az = math.degrees(math.acos(cos_az))
        if math.sin(hour_angle) > 0.0:
            az = 360.0 - az
    return az % 360.0, alt


def local_space_vectors(
    moment: datetime,
    latitude: float,
    longitude: float,
    *,
    bodies: Iterable[str] | None = None,
    adapter: SwissEphemerisAdapter | None = None,
) -> list[LocalSpaceVector]:
    """Return azimuth/altitude vectors for ``bodies`` from a location."""

    _require_swisseph()

    adapter = adapter or SwissEphemerisAdapter.get_default_adapter()
    jd_ut = adapter.julian_day(_moment_to_utc(moment))
    bodies = tuple(bodies) if bodies is not None else _DEFAULT_BODIES

    lst_base = _sidereal_time_degrees(jd_ut, longitude)
    vectors: list[LocalSpaceVector] = []
    for body in bodies:
        code = _resolve_body_code(body)
        equatorial = adapter.body_equatorial(jd_ut, code)
        hour_angle = (lst_base - equatorial.right_ascension) % 360.0
        az, alt = _horizontal_coordinates(hour_angle, equatorial.declination, latitude)
        vectors.append(
            LocalSpaceVector(
                body=body,
                azimuth_deg=az,
                altitude_deg=alt,
                metadata={
                    "ra_deg": equatorial.right_ascension,
                    "decl_deg": equatorial.declination,
                },
            )
        )
    return vectors
