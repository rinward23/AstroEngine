"""Planetary strength scoring for classical dignity conditions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from ..ephemeris import BodyPosition, HousePositions
from ..detectors.ingresses import sign_index, sign_name
from .aspects import GrahaYuddhaOutcome
from .data import (
    COMBUSTION_LIMITS,
    DEBILITATION_SIGNS,
    EXALTATION_SIGNS,
    MOOLATRIKONA_SPANS,
    PLANET_ENEMIES,
    PLANET_FRIENDS,
    SIGN_LORDS,
)
from .utils import circular_separation, degree_in_sign, house_index_for

__all__ = ["StrengthScore", "score_planet_strength"]

DIGNITY_WEIGHTS: Mapping[str, float] = {
    "exaltation": 4.0,
    "moolatrikona": 3.0,
    "own_sign": 2.5,
    "friend_sign": 1.5,
    "neutral_sign": 0.5,
    "enemy_sign": -1.5,
    "debilitation": -4.0,
}

RETROGRADE_BONUS = 1.0
COMBUSTION_PENALTY = -2.5
GRAHA_WAR_WIN_BONUS = 1.5
GRAHA_WAR_LOSS_PENALTY = -3.0

_OWN_SIGN_CACHE: dict[str, tuple[str, ...]] | None = None


def _own_signs() -> dict[str, tuple[str, ...]]:
    global _OWN_SIGN_CACHE
    if _OWN_SIGN_CACHE is None:
        mapping: dict[str, list[str]] = {}
        for sign, lords in SIGN_LORDS.items():
            for lord in lords:
                mapping.setdefault(lord, []).append(sign)
        _OWN_SIGN_CACHE = {planet: tuple(signs) for planet, signs in mapping.items()}
    return _OWN_SIGN_CACHE


def _dignity(planet: str, sign: str, degree: float) -> str:
    if EXALTATION_SIGNS.get(planet) == sign:
        return "exaltation"
    if DEBILITATION_SIGNS.get(planet) == sign:
        return "debilitation"
    span = MOOLATRIKONA_SPANS.get(planet)
    if span and span[0] == sign and span[1] <= degree < span[2]:
        return "moolatrikona"
    if sign in _own_signs().get(planet, ()):  # own sign fallback
        return "own_sign"
    rulers = SIGN_LORDS.get(sign)
    ruler = rulers[0] if rulers else None
    if ruler in PLANET_FRIENDS.get(planet, ()):  # friend sign
        return "friend_sign"
    if ruler in PLANET_ENEMIES.get(planet, ()):  # enemy sign
        return "enemy_sign"
    return "neutral_sign"


@dataclass(frozen=True)
class StrengthScore:
    planet: str
    sign: str
    house: int
    dignity: str
    contributions: Mapping[str, float]
    total: float
    is_retrograde: bool
    is_combust: bool
    graha_yuddha: GrahaYuddhaOutcome | None


def score_planet_strength(
    planet: str,
    position: BodyPosition,
    *,
    houses: HousePositions,
    sun_position: BodyPosition | None = None,
    graha_roles: Mapping[str, tuple[GrahaYuddhaOutcome, str]] | None = None,
) -> StrengthScore:
    """Return a weighted strength score for ``planet`` at ``position``."""

    house_idx = house_index_for(position.longitude, houses)
    sign = sign_name(sign_index(position.longitude))
    degree = degree_in_sign(position.longitude)
    dignity = _dignity(planet, sign, degree)
    contributions: dict[str, float] = {
        "dignity": DIGNITY_WEIGHTS.get(dignity, 0.0)
    }

    is_retrograde = position.speed_longitude < 0
    if is_retrograde:
        contributions["retrograde"] = RETROGRADE_BONUS

    is_combust = False
    if planet != "Sun" and sun_position is not None:
        limit = COMBUSTION_LIMITS.get(planet)
        if limit is not None:
            separation = circular_separation(position.longitude, sun_position.longitude)
            if separation <= limit:
                contributions["combustion"] = COMBUSTION_PENALTY
                is_combust = True

    graha_entry = None
    if graha_roles and planet in graha_roles:
        graha_entry = graha_roles[planet]
        outcome, role = graha_entry
        if role == "winner":
            contributions["graha_yuddha"] = GRAHA_WAR_WIN_BONUS
        else:
            contributions["graha_yuddha"] = GRAHA_WAR_LOSS_PENALTY
    total = sum(contributions.values())
    return StrengthScore(
        planet=planet,
        sign=sign,
        house=house_idx,
        dignity=dignity,
        contributions=contributions,
        total=total,
        is_retrograde=is_retrograde,
        is_combust=is_combust,
        graha_yuddha=graha_entry[0] if graha_entry else None,
    )
