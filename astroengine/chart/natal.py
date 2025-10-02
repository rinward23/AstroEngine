"""Natal chart computation helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

import swisseph as swe

from ..ephemeris import BodyPosition, HousePositions, SwissEphemerisAdapter
from ..scoring import DEFAULT_ASPECTS, OrbCalculator
from .config import ChartConfig

__all__ = [
    "AspectHit",
    "ChartLocation",
    "NatalChart",
    "DEFAULT_BODIES",
    "compute_natal_chart",
]

DEFAULT_BODIES: Mapping[str, int] = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
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
    body_map = bodies or DEFAULT_BODIES
    angles = aspect_angles or DEFAULT_ASPECTS

    jd_ut = adapter.julian_day(moment)
    positions = adapter.body_positions(jd_ut, body_map)
    houses = adapter.houses(jd_ut, location.latitude, location.longitude)
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
