"""Domain and element taxonomy utilities for AstroEngine.

This module centralises the mapping logic for Mind/Body/Spirit
weighting along with the classical element association for zodiac
signs.  The implementation intentionally keeps the defaults easily
inspectable so that downstream profile files can override them without
risking silent regressions.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

# Canonical element labels (uppercase; stable public API)
ELEMENTS: tuple[str, str, str, str] = ("FIRE", "EARTH", "AIR", "WATER")
DOMAINS: tuple[str, str, str] = ("MIND", "BODY", "SPIRIT")

# Zodiac (0=Aries ... 11=Pisces) → Element
ZODIAC_ELEMENT_MAP: tuple[str, ...] = (
    "FIRE",   # 0 Aries
    "EARTH",  # 1 Taurus
    "AIR",    # 2 Gemini
    "WATER",  # 3 Cancer
    "FIRE",   # 4 Leo
    "EARTH",  # 5 Virgo
    "AIR",    # 6 Libra
    "WATER",  # 7 Scorpio
    "FIRE",   # 8 Sagittarius
    "EARTH",  # 9 Capricorn
    "AIR",    # 10 Aquarius
    "WATER",  # 11 Pisces
)

# Planet → default Domain weights (VCA-ish sensible defaults; overridable by profiles)
# Keys use engine’s canonical planet ids: sun, moon, mercury, venus, mars, jupiter, saturn, uranus, neptune, pluto, north_node, south_node, chiron
DEFAULT_PLANET_DOMAIN_WEIGHTS: Mapping[str, Mapping[str, float]] = {
    "sun":     {"SPIRIT": 1.0, "MIND": 0.25, "BODY": 0.25},
    "moon":    {"BODY": 1.0,   "MIND": 0.25},
    "mercury": {"MIND": 1.0},
    "venus":   {"BODY": 0.6,   "SPIRIT": 0.4},
    "mars":    {"BODY": 1.0,   "SPIRIT": 0.3},
    "jupiter": {"SPIRIT": 1.0, "MIND": 0.4},
    "saturn":  {"BODY": 0.7,   "MIND": 0.5},
    "uranus":  {"MIND": 0.9,   "SPIRIT": 0.4},
    "neptune": {"SPIRIT": 1.0},
    "pluto":   {"SPIRIT": 0.7, "BODY": 0.7},
    "north_node": {"SPIRIT": 0.8, "MIND": 0.4},
    "south_node": {"SPIRIT": 0.8, "BODY": 0.4},
    "chiron":  {"BODY": 0.8,   "SPIRIT": 0.5},
}

# House index (1..12) → Domain weights (kept light; debated houses marked TODO for profiles)
DEFAULT_HOUSE_DOMAIN_WEIGHTS: Mapping[int, Mapping[str, float]] = {
    1: {"BODY": 1.0},             # Vitality, soma
    2: {"BODY": 0.7, "MIND": 0.3},
    3: {"MIND": 1.0},             # Communication
    4: {"BODY": 0.6, "SPIRIT": 0.4},
    5: {"SPIRIT": 0.9, "BODY": 0.3},
    6: {"BODY": 1.0},             # Health/routines
    7: {"MIND": 0.6, "SPIRIT": 0.4},
    8: {"SPIRIT": 0.9, "BODY": 0.4},
    9: {"SPIRIT": 0.9, "MIND": 0.6},
    10: {"BODY": 0.6, "SPIRIT": 0.4},
    11: {"MIND": 0.7, "SPIRIT": 0.5},
    12: {"SPIRIT": 1.0},
}


@dataclass(frozen=True)
class DomainResolution:
    elements: list[str]            # e.g., ["FIRE"] (sign-derived)
    domains: dict[str, float]      # merged weights {"MIND": w, ...}


class DomainResolver:
    """Resolve elements and Mind/Body/Spirit domain weights for a transit contact."""

    def __init__(
        self,
        planet_weights: Mapping[str, Mapping[str, float]] | None = None,
        house_weights: Mapping[int, Mapping[str, float]] | None = None,
    ) -> None:
        self._planet = planet_weights or DEFAULT_PLANET_DOMAIN_WEIGHTS
        self._house = house_weights or DEFAULT_HOUSE_DOMAIN_WEIGHTS

    def resolve(
        self,
        sign_index: int,
        planet_key: str,
        house_index: int | None = None,
        overrides: Mapping[str, Mapping] | None = None,
    ) -> DomainResolution:
        if not (0 <= sign_index <= 11):
            raise ValueError("sign_index must be 0..11")
        elements = [ZODIAC_ELEMENT_MAP[sign_index]]

        # Merge weights with shallow override logic
        p = dict(self._planet.get(planet_key, {}))
        h = dict(self._house.get(house_index, {})) if house_index else {}
        if overrides:
            planet_over = overrides.get("planet_weights") if "planet_weights" in overrides else None
            if planet_over and planet_key in planet_over:
                p = dict(planet_over[planet_key])
            house_over = overrides.get("house_weights") if "house_weights" in overrides else None
            if house_over and house_index in house_over:
                h = dict(house_over[house_index])

        merged: dict[str, float] = {}
        for src in (p, h):
            for key, value in src.items():
                merged[key] = merged.get(key, 0.0) + float(value)
        if merged:
            max_value = max(merged.values()) or 1.0
            merged = {key: round(value / max_value, 6) for key, value in merged.items()}
        return DomainResolution(elements=elements, domains=merged)


def natal_domain_factor(
    sign_index: int,
    planet_key: str,
    house_index: int | None,
    multipliers: Mapping[str, float],
    method: str = "weighted",
    temperature: float = 8.0,
) -> float:
    """Compute a domain multiplier for a natal placement using the DomainResolver.

    Returns ``1.0`` if inputs are invalid or if the resolver fails to
    produce domain weights.
    """

    try:
        resolver = DomainResolver()
        resolution = resolver.resolve(sign_index=sign_index, planet_key=planet_key, house_index=house_index)
    except Exception:
        return 1.0
    from .scoring import compute_domain_factor

    return compute_domain_factor(
        resolution.domains,
        multipliers,
        method=method,
        temperature=temperature,
    )


__all__ = [
    "ELEMENTS",
    "DOMAINS",
    "ZODIAC_ELEMENT_MAP",
    "DEFAULT_PLANET_DOMAIN_WEIGHTS",
    "DEFAULT_HOUSE_DOMAIN_WEIGHTS",
    "DomainResolver",
    "DomainResolution",
    "natal_domain_factor",
]
