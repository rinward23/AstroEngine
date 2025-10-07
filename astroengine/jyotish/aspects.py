"""Aspect utilities covering whole-sign drishti and graha yuddha."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ..detectors.ingresses import sign_index, sign_name
from ..ephemeris import BodyPosition, HousePositions
from .data import (
    PLANETARY_WAR_BRIGHTNESS,
    PLANETARY_WAR_PARTICIPANTS,
    SRISHTI_ASPECT_OFFSETS,
)
from .utils import circular_separation, planet_house_map

__all__ = [
    "SrishtiAspect",
    "GrahaYuddhaOutcome",
    "compute_srishti_aspects",
    "detect_graha_yuddha",
]


@dataclass(frozen=True)
class SrishtiAspect:
    planet: str
    source_house: int
    target_house: int
    offset: int
    aspect_type: str
    weight: float


@dataclass(frozen=True)
class GrahaYuddhaOutcome:
    planets: tuple[str, str]
    sign: str
    orb: float
    winner: str
    loser: str
    rationale: str


def compute_srishti_aspects(
    positions: Mapping[str, BodyPosition], houses: HousePositions
) -> list[SrishtiAspect]:
    """Return the whole-sign (Parasara) aspects present in the chart."""

    house_map = planet_house_map(positions, houses)
    aspects: list[SrishtiAspect] = []
    for planet, house_idx in house_map.items():
        offsets = SRISHTI_ASPECT_OFFSETS.get(planet, (7,))
        for offset in offsets:
            target = ((house_idx + offset - 1) % 12) + 1
            aspect_type = "full" if offset == 7 else "special"
            weight = 1.0 if aspect_type == "full" else 0.75
            aspects.append(
                SrishtiAspect(
                    planet=planet,
                    source_house=house_idx,
                    target_house=target,
                    offset=offset,
                    aspect_type=aspect_type,
                    weight=weight,
                )
            )
    return aspects


def _brightness_rank(planet: str) -> int:
    return PLANETARY_WAR_BRIGHTNESS.get(planet, 0)


def detect_graha_yuddha(
    positions: Mapping[str, BodyPosition], *, orb_limit: float = 1.0
) -> list[GrahaYuddhaOutcome]:
    """Return graha yuddha encounters using the classical Parasara rule."""

    outcomes: list[GrahaYuddhaOutcome] = []
    bodies = [p for p in PLANETARY_WAR_PARTICIPANTS if p in positions]
    for idx, planet_a in enumerate(bodies):
        pos_a = positions[planet_a]
        sign_a = sign_index(pos_a.longitude)
        for planet_b in bodies[idx + 1 :]:
            pos_b = positions[planet_b]
            if sign_index(pos_b.longitude) != sign_a:
                continue
            orb = circular_separation(pos_a.longitude, pos_b.longitude)
            if orb > orb_limit:
                continue
            lat_a = pos_a.latitude
            lat_b = pos_b.latitude
            if abs(lat_a - lat_b) > 1e-6:
                winner = planet_a if lat_a > lat_b else planet_b
                rationale = "higher_latitude"
            else:
                rank_a = _brightness_rank(planet_a)
                rank_b = _brightness_rank(planet_b)
                if rank_a != rank_b:
                    winner = planet_a if rank_a > rank_b else planet_b
                    rationale = "brightness_order"
                else:
                    lon_a = pos_a.longitude % 360.0
                    lon_b = pos_b.longitude % 360.0
                    winner = planet_a if lon_a > lon_b else planet_b
                    rationale = "greater_longitude"
            loser = planet_b if winner == planet_a else planet_a
            outcome = GrahaYuddhaOutcome(
                planets=tuple(sorted((planet_a, planet_b))),
                sign=sign_name(sign_a),
                orb=orb,
                winner=winner,
                loser=loser,
                rationale=rationale,
            )
            outcomes.append(outcome)
    return outcomes
