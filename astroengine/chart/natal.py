"""Natal chart computation helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from ..ephemeris import BodyPosition, HousePositions, SwissEphemerisAdapter
from ..scoring import DEFAULT_ASPECTS, OrbCalculator
from ..utils.angles import norm360
from .config import ChartConfig

__all__ = [
    "AspectHit",
    "ChartLocation",
    "NatalChart",
    "DEFAULT_BODIES",
    "compute_natal_chart",
    "BODY_EXPANSIONS",
    "build_body_map",
    "expansions_from_groups",
]

# Swiss Ephemeris body indexes (Sun=0 … Pluto=9) remain stable across releases.
DEFAULT_BODIES: Mapping[str, int] = {
    "Sun": 0,
    "Moon": 1,
    "Mercury": 2,
    "Venus": 3,
    "Mars": 4,
    "Jupiter": 5,
    "Saturn": 6,
    "Uranus": 7,
    "Neptune": 8,
    "Pluto": 9,
}

# Optional expansions keyed by toggle identifiers. Codes follow Swiss ephemeris
# body IDs where applicable. Points without dedicated body IDs (Vertex) are
# handled separately after house computations.
BODY_EXPANSIONS: Mapping[str, Mapping[str, int]] = {
    "asteroids": {
        "Ceres": 17,
        "Pallas": 18,
        "Juno": 19,
        "Vesta": 20,
    },
    "chiron": {"Chiron": 15},
    "mean_lilith": {"Black Moon Lilith (Mean)": 12},
    "true_lilith": {"Black Moon Lilith (True)": 13},
    "mean_node": {
        "Mean Node": 10,
        "Mean South Node": 10,
    },
    "true_node": {
        "True Node": 11,
        "True South Node": 11,
    },
}

_POINT_EXPANSIONS: Mapping[str, tuple[str, ...]] = {
    "vertex": ("Vertex", "Anti-Vertex"),
}


def _point_body_position(name: str, longitude: float, julian_day: float) -> BodyPosition:
    """Return a :class:`BodyPosition` for longitude-only chart points."""

    lon = norm360(longitude)
    return BodyPosition(
        body=name,
        julian_day=float(julian_day),
        longitude=lon,
        latitude=0.0,
        distance_au=0.0,
        speed_longitude=0.0,
        speed_latitude=0.0,
        speed_distance=0.0,
        declination=0.0,
        speed_declination=0.0,
    )


def build_body_map(
    expansions: Mapping[str, bool] | None = None,
    *,
    base: Mapping[str, int] | None = None,
) -> dict[str, int]:
    """Return a body→code mapping with optional expansion groups applied."""

    mapping = dict(base or DEFAULT_BODIES)
    if not expansions:
        return mapping

    for key, enabled in expansions.items():
        if not enabled:
            continue
        extra = BODY_EXPANSIONS.get(key)
        if not extra:
            continue
        for name, code in extra.items():
            mapping.setdefault(name, code)
    return mapping


def expansions_from_groups(
    groups: Mapping[str, bool] | None,
) -> dict[str, bool]:
    """Translate UI/config body groups into ``compute_natal_chart`` expansions."""

    if not groups:
        return {}
    return {
        "asteroids": bool(groups.get("asteroids_major")),
        "chiron": bool(groups.get("chiron") or groups.get("centaurs")),
        "mean_lilith": bool(groups.get("lilith_mean")),
        "true_lilith": bool(groups.get("lilith_true")),
        "mean_node": bool(groups.get("nodes_mean")),
        "true_node": bool(groups.get("nodes_true")),
        "vertex": bool(groups.get("vertex")),
    }


@dataclass(frozen=True)
class ChartLocation:
    """Simple latitude/longitude pair used for house calculations."""

    latitude: float
    longitude: float


@dataclass(frozen=True)
class AspectHit:
    """Represents an aspect between two bodies within an orb allowance."""

    body_a: str
    body_b: str
    angle: int
    orb: float
    separation: float


@dataclass(frozen=True)
class NatalChart:
    """Computed positions and derived metadata for a natal event."""

    moment: datetime
    location: ChartLocation
    julian_day: float
    positions: Mapping[str, BodyPosition]
    houses: HousePositions
    aspects: Sequence[AspectHit]
    zodiac: str = "tropical"
    ayanamsa: str | None = None
    ayanamsa_degrees: float | None = None
    metadata: Mapping[str, object] | None = None


def _circular_delta(a: float, b: float) -> float:
    diff = (b - a) % 360.0
    return diff if diff <= 180.0 else 360.0 - diff


def _compute_aspects(
    positions: Mapping[str, BodyPosition],
    aspect_angles: Sequence[int],
    orb_calculator: OrbCalculator,
    profile: str,
) -> list[AspectHit]:
    hits: list[AspectHit] = []
    body_names = list(positions.keys())
    for idx, name_a in enumerate(body_names):
        for name_b in body_names[idx + 1 :]:
            pos_a = positions[name_a].longitude
            pos_b = positions[name_b].longitude
            separation = _circular_delta(pos_a, pos_b)
            for angle in aspect_angles:
                orb = abs(separation - angle)
                threshold = orb_calculator.orb_for(
                    name_a, name_b, angle, profile=profile
                )
                if orb <= threshold:
                    hits.append(
                        AspectHit(
                            body_a=name_a,
                            body_b=name_b,
                            angle=int(angle),
                            orb=orb,
                            separation=separation,
                        )
                    )
                    break
    return hits


def compute_natal_chart(
    moment: datetime,
    location: ChartLocation,
    *,
    bodies: Mapping[str, int] | None = None,
    body_expansions: Mapping[str, bool] | None = None,
    aspect_angles: Sequence[int] | None = None,
    orb_profile: str = "standard",
    config: ChartConfig | None = None,
    adapter: SwissEphemerisAdapter | None = None,
    orb_calculator: OrbCalculator | None = None,
) -> NatalChart:
    """Compute a natal chart snapshot using Swiss Ephemeris data."""

    chart_config = config or ChartConfig()
    adapter = adapter or SwissEphemerisAdapter.from_chart_config(chart_config)

    orb_calculator = orb_calculator or OrbCalculator()
    body_map = build_body_map(body_expansions, base=bodies or DEFAULT_BODIES)
    angles = aspect_angles or DEFAULT_ASPECTS

    jd_ut = adapter.julian_day(moment)
    positions: dict[str, BodyPosition] = dict(
        adapter.body_positions(jd_ut, body_map)
    )
    houses = adapter.houses(jd_ut, location.latitude, location.longitude)

    expansions = body_expansions or {}
    if expansions.get("vertex"):
        labels = _POINT_EXPANSIONS.get("vertex", ())
        longitudes = (houses.vertex, houses.antivertex)
        for label, longitude in zip(labels, longitudes, strict=False):
            if longitude is None:
                continue
            positions[label] = _point_body_position(label, longitude, jd_ut)

    aspects = _compute_aspects(positions, list(angles), orb_calculator, orb_profile)

    zodiac = chart_config.zodiac
    ayanamsa_name = chart_config.ayanamsha if zodiac == "sidereal" else None
    ayanamsa_degrees = adapter.ayanamsa(jd_ut) if ayanamsa_name else None
    provenance: dict[str, object] = {"zodiac": zodiac, "house_system": chart_config.house_system}
    if ayanamsa_name:
        provenance.update(
            {
                "ayanamsa": ayanamsa_name,
                "ayanamsa_degrees": ayanamsa_degrees,
                "ayanamsa_source": "swisseph",
            }
        )
        provenance["nodes_variant"] = chart_config.nodes_variant
        provenance["lilith_variant"] = chart_config.lilith_variant
    else:
        provenance["nodes_variant"] = chart_config.nodes_variant
        provenance["lilith_variant"] = chart_config.lilith_variant

    return NatalChart(
        moment=moment,
        location=location,
        julian_day=jd_ut,
        positions=positions,
        houses=houses,
        aspects=tuple(aspects),
        zodiac=zodiac,
        ayanamsa=ayanamsa_name,
        ayanamsa_degrees=ayanamsa_degrees,
        metadata=provenance,
    )
