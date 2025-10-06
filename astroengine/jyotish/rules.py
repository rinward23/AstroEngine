"""House claim resolution based on Jyotish strength scoring."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from ..chart.natal import NatalChart
from ..ephemeris import BodyPosition, HousePositions
from .aspects import GrahaYuddhaOutcome, compute_srishti_aspects, detect_graha_yuddha
from .karaka import match_karakas
from .lords import determine_house_lords, house_occupants
from .strength import StrengthScore, score_planet_strength
from .utils import house_signs

__all__ = [
    "HouseClaim",
    "HouseWinner",
    "evaluate_house_claims",
    "evaluate_house_claims_from_chart",
]

CLAIM_WEIGHTS: Mapping[str, float] = {
    "ruler": 2.5,
    "co_ruler": 2.0,
    "occupant": 1.8,
    "karaka": 1.2,
    "aspect_full": 1.0,
    "aspect_special": 0.8,
}

CLAIM_PRIORITY: Mapping[str, int] = {
    "ruler": 0,
    "co_ruler": 1,
    "occupant": 2,
    "karaka": 3,
    "aspect_full": 4,
    "aspect_special": 5,
}


@dataclass(frozen=True)
class HouseClaim:
    planet: str
    claim_type: str
    basis: str
    weight: float
    strength: StrengthScore
    effective_score: float
    metadata: Mapping[str, object] | None = None


@dataclass(frozen=True)
class HouseWinner:
    house: int
    sign: str
    winner: HouseClaim | None
    claims: tuple[HouseClaim, ...]
    graha_yuddha: tuple[GrahaYuddhaOutcome, ...]


def _claim_sort_key(claim: HouseClaim) -> tuple[float, int, float, float, str]:
    priority = CLAIM_PRIORITY.get(claim.claim_type, 99)
    return (
        -claim.effective_score,
        priority,
        -claim.strength.total,
        -claim.weight,
        claim.planet,
    )


def _build_graha_roles(
    outcomes: Iterable[GrahaYuddhaOutcome],
) -> dict[str, tuple[GrahaYuddhaOutcome, str]]:
    roles: dict[str, tuple[GrahaYuddhaOutcome, str]] = {}
    for outcome in outcomes:
        roles[outcome.winner] = (outcome, "winner")
        roles[outcome.loser] = (outcome, "loser")
    return roles


def evaluate_house_claims(
    positions: Mapping[str, BodyPosition],
    houses: HousePositions,
    *,
    include_co_lords: bool = True,
) -> dict[int, HouseWinner]:
    """Return the resolved house winners for the supplied chart geometry."""

    lords = determine_house_lords(houses, include_co_lords=include_co_lords)
    occupants = house_occupants(positions, houses)
    karaka_matches = {
        house: match_karakas(house, positions) for house in range(1, 13)
    }
    aspects = compute_srishti_aspects(positions, houses)
    aspect_targets: dict[int, list] = {}
    for aspect in aspects:
        aspect_targets.setdefault(aspect.target_house, []).append(aspect)

    graha_outcomes = detect_graha_yuddha(positions)
    graha_roles = _build_graha_roles(graha_outcomes)

    sun_position = positions.get("Sun")
    strengths: dict[str, StrengthScore] = {}
    for planet, position in positions.items():
        strengths[planet] = score_planet_strength(
            planet,
            position,
            houses=houses,
            sun_position=sun_position,
            graha_roles=graha_roles,
        )

    claims_by_house: dict[int, list[HouseClaim]] = {house: [] for house in range(1, 13)}
    sign_map = house_signs(houses)

    for house in range(1, 13):
        house_claims = claims_by_house[house]
        sign = sign_map[house]

        for idx, planet in enumerate(lords.get(house, ())):
            if planet not in strengths:
                continue
            claim_type = "ruler" if idx == 0 else "co_ruler"
            weight = CLAIM_WEIGHTS[claim_type]
            basis = f"{sign} {'ruler' if idx == 0 else 'co-ruler'}"
            strength = strengths[planet]
            effective = weight + strength.total
            house_claims.append(
                HouseClaim(
                    planet=planet,
                    claim_type=claim_type,
                    basis=basis,
                    weight=weight,
                    strength=strength,
                    effective_score=effective,
                    metadata={"ordinal": idx},
                )
            )

        for planet in occupants.get(house, ()):  # occupant weight
            if planet not in strengths:
                continue
            weight = CLAIM_WEIGHTS["occupant"]
            strength = strengths[planet]
            effective = weight + strength.total
            house_claims.append(
                HouseClaim(
                    planet=planet,
                    claim_type="occupant",
                    basis="occupant",
                    weight=weight,
                    strength=strength,
                    effective_score=effective,
                    metadata={"longitude": positions[planet].longitude},
                )
            )

        for planet in karaka_matches.get(house, ()):  # karakas present
            if planet not in strengths:
                continue
            weight = CLAIM_WEIGHTS["karaka"]
            strength = strengths[planet]
            effective = weight + strength.total
            house_claims.append(
                HouseClaim(
                    planet=planet,
                    claim_type="karaka",
                    basis="natural_karaka",
                    weight=weight,
                    strength=strength,
                    effective_score=effective,
                    metadata=None,
                )
            )

        for aspect in aspect_targets.get(house, ()):  # drishti
            planet = aspect.planet
            if planet not in strengths:
                continue
            claim_type = "aspect_full" if aspect.aspect_type == "full" else "aspect_special"
            base_weight = CLAIM_WEIGHTS[claim_type]
            weight = base_weight * aspect.weight
            strength = strengths[planet]
            effective = weight + strength.total
            house_claims.append(
                HouseClaim(
                    planet=planet,
                    claim_type=claim_type,
                    basis=f"srishti_{aspect.aspect_type}",
                    weight=weight,
                    strength=strength,
                    effective_score=effective,
                    metadata={
                        "source_house": aspect.source_house,
                        "offset": aspect.offset,
                    },
                )
            )

    winners: dict[int, HouseWinner] = {}
    for house, claims in claims_by_house.items():
        claims_sorted = sorted(claims, key=_claim_sort_key)
        winner_claim = claims_sorted[0] if claims_sorted else None
        winners[house] = HouseWinner(
            house=house,
            sign=sign_map[house],
            winner=winner_claim,
            claims=tuple(claims_sorted),
            graha_yuddha=tuple(graha_outcomes),
        )
    return winners


def evaluate_house_claims_from_chart(chart: NatalChart) -> dict[int, HouseWinner]:
    """Convenience wrapper accepting a :class:`NatalChart`."""

    return evaluate_house_claims(chart.positions, chart.houses)
