"""Domain and element taxonomy utilities for AstroEngine.

This module provides deterministic mappings between zodiac signs,
planets, houses, and their corresponding VCA Mind/Body/Spirit domain
weights.  The goal is to make the tagging logic fully data-driven so it
can be reused by the engine, exporters, and any diagnostic tooling
without risking accidental module loss.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Tuple

# >>> AUTO-GEN BEGIN: Domains & Elements v1.0

# Canonical element labels (uppercase; stable public API)
ELEMENTS: Tuple[str, str, str, str] = ("FIRE", "EARTH", "AIR", "WATER")
DOMAINS: Tuple[str, str, str] = ("MIND", "BODY", "SPIRIT")

# Zodiac (0=Aries ... 11=Pisces) → Element
ZODIAC_ELEMENT_MAP: Tuple[str, ...] = (
    "FIRE",  # 0 Aries
    "EARTH",  # 1 Taurus
    "AIR",  # 2 Gemini
    "WATER",  # 3 Cancer
    "FIRE",  # 4 Leo
    "EARTH",  # 5 Virgo
    "AIR",  # 6 Libra
    "WATER",  # 7 Scorpio
    "FIRE",  # 8 Sagittarius
    "EARTH",  # 9 Capricorn
    "AIR",  # 10 Aquarius
    "WATER",  # 11 Pisces
)

# Planet → default Domain weights (VCA-ish sensible defaults; overridable by profiles)
# Keys use engine’s canonical planet ids: sun, moon, mercury, venus, mars, jupiter, saturn,
# uranus, neptune, pluto, north_node, south_node, chiron
DEFAULT_PLANET_DOMAIN_WEIGHTS: Mapping[str, Mapping[str, float]] = {
    "sun": {"SPIRIT": 1.0, "MIND": 0.25, "BODY": 0.25},
    "moon": {"BODY": 1.0, "MIND": 0.25},
    "mercury": {"MIND": 1.0},
    "venus": {"BODY": 0.6, "SPIRIT": 0.4},
    "mars": {"BODY": 1.0, "SPIRIT": 0.3},
    "jupiter": {"SPIRIT": 1.0, "MIND": 0.4},
    "saturn": {"BODY": 0.7, "MIND": 0.5},
    "uranus": {"MIND": 0.9, "SPIRIT": 0.4},
    "neptune": {"SPIRIT": 1.0},
    "pluto": {"SPIRIT": 0.7, "BODY": 0.7},
    "north_node": {"SPIRIT": 0.8, "MIND": 0.4},
    "south_node": {"SPIRIT": 0.8, "BODY": 0.4},
    "chiron": {"BODY": 0.8, "SPIRIT": 0.5},
}

# House index (1..12) → Domain weights (kept light; debated houses marked TODO for profiles)
DEFAULT_HOUSE_DOMAIN_WEIGHTS: Mapping[int, Mapping[str, float]] = {
    1: {"BODY": 1.0},  # Vitality, soma
    2: {"BODY": 0.7, "MIND": 0.3},
    3: {"MIND": 1.0},  # Communication
    4: {"BODY": 0.6, "SPIRIT": 0.4},
    5: {"SPIRIT": 0.9, "BODY": 0.3},
    6: {"BODY": 1.0},  # Health/routines
    7: {"MIND": 0.6, "SPIRIT": 0.4},
    8: {"SPIRIT": 0.9, "BODY": 0.4},
    9: {"SPIRIT": 0.9, "MIND": 0.6},
    10: {"BODY": 0.6, "SPIRIT": 0.4},
    11: {"MIND": 0.7, "SPIRIT": 0.5},
    12: {"SPIRIT": 1.0},
}


@dataclass(frozen=True)
class DomainResolution:
    elements: List[str]  # e.g., ["FIRE"] (sign-derived)
    domains: Dict[str, float]  # merged weights {"MIND": w, ...}


class DomainResolver:
    """Resolve Elements (by sign) and Mind/Body/Spirit domain weights for a transit contact."""

    def __init__(
        self,
        planet_weights: Optional[Mapping[str, Mapping[str, float]]] = None,
        house_weights: Optional[Mapping[int, Mapping[str, float]]] = None,
    ) -> None:
        self._planet = planet_weights or DEFAULT_PLANET_DOMAIN_WEIGHTS
        self._house = house_weights or DEFAULT_HOUSE_DOMAIN_WEIGHTS

    def resolve(
        self,
        sign_index: int,
        planet_key: str,
        house_index: Optional[int] = None,
        overrides: Optional[Mapping[str, Mapping]] = None,
    ) -> DomainResolution:
        if not (0 <= sign_index <= 11):
            raise ValueError("sign_index must be 0..11")
        elements = [ZODIAC_ELEMENT_MAP[sign_index]]

        # Merge weights with shallow override logic
        planet_weights = dict(self._planet.get(planet_key, {}))
        house_weights = dict(self._house.get(house_index, {})) if house_index else {}
        if overrides:
            planet_override = overrides.get("planet_weights") if hasattr(overrides, "get") else None
            if planet_override and planet_key in planet_override:
                planet_weights = dict(planet_override[planet_key])
            house_override = overrides.get("house_weights") if hasattr(overrides, "get") else None
            if house_override and house_index in house_override:
                house_weights = dict(house_override[house_index])

        merged: Dict[str, float] = {}
        for src in (planet_weights, house_weights):
            for key, value in src.items():
                merged[key] = merged.get(key, 0.0) + float(value)
        if merged:
            maximum = max(merged.values()) or 1.0
            merged = {key: round(value / maximum, 6) for key, value in merged.items()}
        return DomainResolution(elements=elements, domains=merged)


# >>> AUTO-GEN END: Domains & Elements v1.0


# >>> AUTO-GEN BEGIN: Natal Domain Factor Helper v1.1
def natal_domain_factor(
    sign_index: int,
    planet_key: str,
    house_index: Optional[int],
    multipliers: Mapping[str, float],
    method: str = "weighted",
    temperature: float = 8.0,
) -> float:
    """Compute a domain multiplier for a natal placement.

    Returns 1.0 if resolution fails or no domain weights are produced.
    """

    try:
        resolver = DomainResolver()
        result = resolver.resolve(
            sign_index=sign_index,
            planet_key=planet_key,
            house_index=house_index,
        )
    except Exception:
        return 1.0
    if not result.domains:
        return 1.0
    from .scoring import compute_domain_factor

    return compute_domain_factor(
        result.domains,
        multipliers,
        method=method,
        temperature=temperature,
    )


# >>> AUTO-GEN END: Natal Domain Factor Helper v1.1


__all__ = [
    "DomainResolver",
    "DomainResolution",
    "ELEMENTS",
    "DOMAINS",
    "ZODIAC_ELEMENT_MAP",
    "DEFAULT_PLANET_DOMAIN_WEIGHTS",
    "DEFAULT_HOUSE_DOMAIN_WEIGHTS",
    "natal_domain_factor",
]

