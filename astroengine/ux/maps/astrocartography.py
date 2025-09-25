"""Locational mapping helpers built on Swiss ephemeris data."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

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

_BODY_RESOLVERS: Mapping[str, str] = {
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
class MapLine:
    """Polyline describing where a celestial body is angular."""

    body: str
    kind: str
    coordinates: tuple[tuple[float, float], ...]
    metadata: Mapping[str, float] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "body": self.body,
            "kind": self.kind,
            "coordinates": [list(point) for point in self.coordinates],
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class LocalSpaceVector:
    """Azimuth/altitude vector for a body from a specific location."""

    body: str
    azimuth_deg: float
    altitude_deg: float
    metadata: Mapping[str, float] = field(default_factory=dict)

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


def _normalize_longitude(value: float) -> float:
    wrapped = (value + 180.0) % 360.0 - 180.0
    if wrapped == -180.0:
        return 180.0
    return wrapped


def _meridian_track(
    longitude: float, *, step_deg: float = 2.0
) -> tuple[tuple[float, float], ...]:
    coordinates: list[tuple[float, float]] = []
    lat = -90.0
    while lat <= 90.0 + 1e-6:
        coordinates.append(
            (_normalize_longitude(longitude), max(min(lat, 90.0), -90.0))
        )
        lat += step_deg
    return tuple(coordinates)


def _horizon_tracks(
    ra_deg: float,
    decl_deg: float,
    gst_deg: float,
    *,
    step_deg: float = 1.5,
) -> tuple[tuple[tuple[float, float], ...], tuple[tuple[float, float], ...]]:
    asc: list[tuple[float, float]] = []
    dsc: list[tuple[float, float]] = []
    delta_rad = math.radians(decl_deg)
    if abs(math.cos(delta_rad)) < 1e-6:
        return tuple(asc), tuple(dsc)
    lat = -88.5
    while lat <= 88.5 + 1e-6:
        phi = math.radians(lat)
        tan_phi = math.tan(phi)
        tan_delta = math.tan(delta_rad)
        cos_h = -tan_phi * tan_delta
        if abs(cos_h) <= 1.0:
            hour_angle = math.degrees(math.acos(max(-1.0, min(1.0, cos_h))))
            lon_rise = _normalize_longitude(ra_deg - hour_angle - gst_deg)
            lon_set = _normalize_longitude(ra_deg + hour_angle - gst_deg)
            asc.append((lon_rise, lat))
            dsc.append((lon_set, lat))
        lat += step_deg
    asc.sort(key=lambda item: item[1])
    dsc.sort(key=lambda item: item[1])
    return tuple(asc), tuple(dsc)


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

    _require_swisseph()

    adapter = adapter or SwissEphemerisAdapter.get_default_adapter()
    bodies = tuple(bodies) if bodies is not None else _DEFAULT_BODIES
    jd_ut = adapter.julian_day(_moment_to_utc(moment))
    gst_hours = swe.sidtime(jd_ut)
    gst_deg = (gst_hours * 15.0) % 360.0

    lines: list[MapLine] = []
    for body in bodies:
        code = _resolve_body_code(body)
        equatorial = adapter.body_equatorial(jd_ut, code)
        ra_deg = equatorial.right_ascension
        decl_deg = equatorial.declination

        mc_long = _normalize_longitude(ra_deg - gst_deg)
        lines.append(
            MapLine(
                body=body,
                kind="MC",
                coordinates=_meridian_track(mc_long, step_deg=lat_step),
                metadata={"ra_deg": ra_deg, "decl_deg": decl_deg},
            )
        )
        ic_long = _normalize_longitude(mc_long + 180.0)
        lines.append(
            MapLine(
                body=body,
                kind="IC",
                coordinates=_meridian_track(ic_long, step_deg=lat_step),
                metadata={"ra_deg": ra_deg, "decl_deg": decl_deg},
            )
        )

        asc_track, dsc_track = _horizon_tracks(
            ra_deg, decl_deg, gst_deg, step_deg=lat_step
        )
        if asc_track:
            lines.append(
                MapLine(
                    body=body,
                    kind="ASC",
                    coordinates=asc_track,
                    metadata={"ra_deg": ra_deg, "decl_deg": decl_deg},
                )
            )
        if dsc_track:
            lines.append(
                MapLine(
                    body=body,
                    kind="DSC",
                    coordinates=dsc_track,
                    metadata={"ra_deg": ra_deg, "decl_deg": decl_deg},
                )
            )

    return lines


def _sidereal_time_degrees(jd_ut: float, longitude: float) -> float:
    gst_hours = swe.sidtime(jd_ut)
    return (gst_hours * 15.0 + longitude) % 360.0


def _horizontal_coordinates(
    hour_angle_deg: float, decl_deg: float, latitude_deg: float
) -> tuple[float, float]:
    hour_angle = math.radians(hour_angle_deg)
    delta = math.radians(decl_deg)
    phi = math.radians(latitude_deg)
    sin_alt = math.sin(delta) * math.sin(phi) + math.cos(delta) * math.cos(
        phi
    ) * math.cos(hour_angle)
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
