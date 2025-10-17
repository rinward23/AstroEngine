"""Astrocartography linework and relocation helpers."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

from astroengine.ephemeris import SwissEphemerisAdapter
from astroengine.ephemeris.swe import has_swe, swe

__all__ = [
    "AstrocartographyResult",
    "MapLine",
    "compute_astrocartography_lines",
]

_AngleKinds = {"ASC", "DSC", "MC", "IC"}

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

_HAS_SWE = has_swe()

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
class AstrocartographyResult:
    """Container bundling linework (and optional paran hits)."""

    lines: tuple[MapLine, ...]
    parans: tuple[dict[str, object], ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, object]:
        return {
            "lines": [line.as_dict() for line in self.lines],
            "parans": [dict(item) for item in self.parans],
        }


def _require_swisseph() -> None:
    if not _HAS_SWE:  # pragma: no cover - dependency guard
        raise RuntimeError(
            "Astrocartography helpers require pyswisseph. Install AstroEngine with "
            "the 'locational' extra to enable maps."
        )


def _resolve_body_code(name: str) -> int:
    resolver = _BODY_RESOLVERS.get(name.lower())
    if resolver is None:
        raise KeyError(f"Unsupported body for locational maps: {name}")
    _require_swisseph()
    swe_module = swe()
    code = getattr(swe_module, resolver, None)
    if code is None:
        raise KeyError(f"Swiss Ephemeris does not expose constant '{resolver}'")
    return int(code)


def _normalize_longitude(value: float) -> float:
    wrapped = (value + 180.0) % 360.0 - 180.0
    if wrapped == -180.0:
        return 180.0
    return wrapped


def _normalize_relative(value: float, reference: float) -> float:
    """Shift ``value`` onto the longitude branch near ``reference``."""

    adjusted = value
    while adjusted - reference > 180.0:
        adjusted -= 360.0
    while adjusted - reference < -180.0:
        adjusted += 360.0
    return adjusted


def _meridian_track(longitude: float, *, step_deg: float = 2.0) -> tuple[tuple[float, float], ...]:
    coordinates: list[tuple[float, float]] = []
    lat = -90.0
    while lat <= 90.0 + 1e-6:
        coordinates.append((_normalize_longitude(longitude), max(min(lat, 90.0), -90.0)))
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


def _perpendicular_distance(
    point: tuple[float, float], start: tuple[float, float], end: tuple[float, float]
) -> float:
    (x0, y0), (x1, y1), (x2, y2) = point, start, end
    if (x1, y1) == (x2, y2):
        return math.hypot(x0 - x1, y0 - y1)
    numerator = abs((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1)
    denominator = math.hypot(x2 - x1, y2 - y1)
    if denominator == 0.0:
        return 0.0
    return numerator / denominator


def _angular_separation(
    ra1_deg: float | None,
    dec1_deg: float | None,
    ra2_deg: float | None,
    dec2_deg: float | None,
) -> float | None:
    """Return the angular separation between two equatorial coordinates."""

    if None in (ra1_deg, dec1_deg, ra2_deg, dec2_deg):
        return None

    ra1 = math.radians(ra1_deg)
    dec1 = math.radians(dec1_deg)
    ra2 = math.radians(ra2_deg)
    dec2 = math.radians(dec2_deg)
    cos_angle = (
        math.sin(dec1) * math.sin(dec2)
        + math.cos(dec1) * math.cos(dec2) * math.cos(ra1 - ra2)
    )
    cos_angle = max(-1.0, min(1.0, cos_angle))
    return math.degrees(math.acos(cos_angle))


def _rdp_simplify(
    coordinates: tuple[tuple[float, float], ...], tolerance: float
) -> tuple[tuple[float, float], ...]:
    if tolerance <= 0.0 or len(coordinates) < 3:
        return coordinates

    start, end = coordinates[0], coordinates[-1]
    max_distance = 0.0
    index = 0
    for i in range(1, len(coordinates) - 1):
        dist = _perpendicular_distance(coordinates[i], start, end)
        if dist > max_distance:
            index = i
            max_distance = dist

    if max_distance > tolerance:
        left = _rdp_simplify(coordinates[: index + 1], tolerance)
        right = _rdp_simplify(coordinates[index:], tolerance)
        return left[:-1] + right
    return (start, end)


def compute_astrocartography_lines(
    moment: datetime,
    *,
    bodies: Sequence[str] | None = None,
    adapter: SwissEphemerisAdapter | None = None,
    lat_step: float = 1.5,
    line_types: Iterable[str] | None = None,
    simplify_tolerance: float = 0.5,
    show_parans: bool = False,
) -> AstrocartographyResult:
    """Return astrocartography lines for ``moment`` with optional parans."""

    _require_swisseph()

    adapter = adapter or SwissEphemerisAdapter.get_default_adapter()
    bodies = tuple(bodies) if bodies is not None else _DEFAULT_BODIES
    requested_kinds = {kind.upper() for kind in (line_types or _AngleKinds)} & _AngleKinds
    if not requested_kinds:
        raise ValueError("At least one line type must be requested")

    jd_ut = adapter.julian_day(_moment_to_utc(moment))
    swe_module = swe()
    gst_hours = swe_module.sidtime(jd_ut)
    gst_deg = (gst_hours * 15.0) % 360.0

    lines: list[MapLine] = []
    for body in bodies:
        code = _resolve_body_code(body)
        equatorial = adapter.body_equatorial(jd_ut, code)
        ra_deg = equatorial.right_ascension
        decl_deg = equatorial.declination
        metadata = {"ra_deg": ra_deg, "decl_deg": decl_deg}

        mc_long = _normalize_longitude(ra_deg - gst_deg)
        if "MC" in requested_kinds:
            track = _meridian_track(mc_long, step_deg=lat_step)
            track = _rdp_simplify(track, simplify_tolerance)
            lines.append(MapLine(body=body, kind="MC", coordinates=track, metadata=metadata))
        if "IC" in requested_kinds:
            ic_long = _normalize_longitude(mc_long + 180.0)
            track = _meridian_track(ic_long, step_deg=lat_step)
            track = _rdp_simplify(track, simplify_tolerance)
            lines.append(MapLine(body=body, kind="IC", coordinates=track, metadata=metadata))

        asc_track, dsc_track = _horizon_tracks(ra_deg, decl_deg, gst_deg, step_deg=lat_step)
        if asc_track and "ASC" in requested_kinds:
            lines.append(
                MapLine(
                    body=body,
                    kind="ASC",
                    coordinates=_rdp_simplify(asc_track, simplify_tolerance),
                    metadata=metadata,
                )
            )
        if dsc_track and "DSC" in requested_kinds:
            lines.append(
                MapLine(
                    body=body,
                    kind="DSC",
                    coordinates=_rdp_simplify(dsc_track, simplify_tolerance),
                    metadata=metadata,
                )
            )

    parans: tuple[dict[str, object], ...] = tuple()
    if show_parans:
        lines_by_kind: dict[str, list[MapLine]] = {kind: [] for kind in _AngleKinds}
        for line in lines:
            lines_by_kind.setdefault(line.kind, []).append(line)

        paran_markers: list[dict[str, object]] = []
        seen: set[tuple[object, ...]] = set()
        combinations = (("MC", "ASC"), ("MC", "DSC"), ("IC", "ASC"), ("IC", "DSC"))

        for meridian_kind, horizon_kind in combinations:
            for meridian in lines_by_kind.get(meridian_kind, []):
                if not meridian.coordinates:
                    continue
                longitude = _normalize_longitude(meridian.coordinates[0][0])
                meridian_meta = meridian.metadata
                for horizon in lines_by_kind.get(horizon_kind, []):
                    coords = horizon.coordinates
                    if len(coords) < 2:
                        continue
                    horizon_meta = horizon.metadata
                    for idx in range(len(coords) - 1):
                        lon1, lat1 = coords[idx]
                        lon2, lat2 = coords[idx + 1]
                        lon1_adj = _normalize_relative(lon1, longitude)
                        lon2_adj = _normalize_relative(lon2, longitude)
                        if math.isclose(lon1_adj, lon2_adj, abs_tol=1e-9):
                            continue
                        min_lon = min(lon1_adj, lon2_adj)
                        max_lon = max(lon1_adj, lon2_adj)
                        if not (min_lon - 1e-9 <= longitude <= max_lon + 1e-9):
                            continue
                        t = (longitude - lon1_adj) / (lon2_adj - lon1_adj)
                        if t < -1e-6 or t > 1.0 + 1e-6:
                            continue
                        lat = lat1 + t * (lat2 - lat1)
                        if lat < -90.0 - 1e-6 or lat > 90.0 + 1e-6:
                            continue

                        key = (
                            meridian.body,
                            meridian.kind,
                            horizon.body,
                            horizon.kind,
                            round(longitude, 4),
                            round(lat, 4),
                        )
                        if key in seen:
                            continue
                        seen.add(key)

                        dx = lon2_adj - lon1_adj
                        dy = lat2 - lat1
                        magnitude = math.hypot(dx, dy)
                        bearing_angle = None
                        if magnitude > 0.0:
                            cos_theta = max(-1.0, min(1.0, dy / magnitude))
                            bearing_angle = math.degrees(math.acos(cos_theta))

                        angular_sep = _angular_separation(
                            meridian_meta.get("ra_deg") if meridian_meta else None,
                            meridian_meta.get("decl_deg") if meridian_meta else None,
                            horizon_meta.get("ra_deg") if horizon_meta else None,
                            horizon_meta.get("decl_deg") if horizon_meta else None,
                        )

                        metadata: dict[str, float | None] = {
                            "angular_separation_deg": angular_sep,
                        }
                        if bearing_angle is not None:
                            metadata["bearing_difference_deg"] = bearing_angle

                        paran_markers.append(
                            {
                                "coordinates": ((longitude, lat),),
                                "longitude": longitude,
                                "latitude": lat,
                                "primary": {"body": meridian.body, "kind": meridian.kind},
                                "secondary": {"body": horizon.body, "kind": horizon.kind},
                                "metadata": metadata,
                            }
                        )

        parans = tuple(paran_markers)

    return AstrocartographyResult(lines=tuple(lines), parans=parans)
