
"""Body catalogue helpers for gating, scoring, and default profiles."""

from __future__ import annotations

from functools import lru_cache

from typing import Dict, Set

__all__ = [
    "ALL_SUPPORTED_BODIES",
    "body_class",
    "body_priority",
    "canonical_name",
    "step_multiplier",
]



# Canonical body classification including nodes, points, asteroids, and TNOs.
_BODY_CLASS: Dict[str, str] = {
    # Luminaries / classical planets

    "sun": "luminary",
    "moon": "luminary",
    "mercury": "personal",
    "venus": "personal",
    "mars": "personal",
    "jupiter": "social",
    "saturn": "social",
    "uranus": "outer",
    "neptune": "outer",
    "pluto": "outer",

    # Nodes
    "mean_node": "point",
    "true_node": "point",
    "south_node": "point",
    # Asteroids & centaurs

    "ceres": "asteroid",
    "pallas": "asteroid",
    "juno": "asteroid",
    "vesta": "asteroid",
    "chiron": "centaur",
    "pholus": "centaur",
    "nessus": "centaur",

    # Trans-Neptunian / dwarf planets

    "eris": "tno",
    "haumea": "tno",
    "makemake": "tno",
    "sedna": "tno",
    "quaoar": "tno",
    "orcus": "tno",
    "ixion": "tno",

    # Lunar nodes
    "mean_node": "point",
    "true_node": "point",
    "south_node": "point",
    "north_node": "point",
    # Black Moon Lilith variants
    "mean_lilith": "point",
    "true_lilith": "point",
    # Vertex / lots

    "vertex": "point",
    "antivertex": "point",
    "fortune": "point",
    "spirit": "point",
}



_BODY_ALIASES: Dict[str, str] = {

    "north_node": "mean_node",
    "node": "mean_node",
    "nn": "mean_node",
    "sn": "south_node",

    "black_moon_lilith": "mean_lilith",
    "lilith": "mean_lilith",
    "trueblackmoon": "true_lilith",

    "avx": "antivertex",
    "part_of_fortune": "fortune",
    "pof": "fortune",
}


def canonical_name(name: str) -> str:
    """Return the canonical lower-case identifier for ``name``."""

    lowered = (name or "").strip().lower()
    if not lowered:
        return ""
    return _BODY_ALIASES.get(lowered, lowered)


@lru_cache(maxsize=None)
def body_class(name: str) -> str:
    """Return the scoring/gating class for the supplied body name."""


    canonical = canonical_name(name)
    if not canonical:
        return "outer"

    return _BODY_CLASS.get(canonical, "outer")


_ALL_CANONICAL: Set[str] = set(_BODY_CLASS)
ALL_SUPPORTED_BODIES: Set[str] = set(sorted(_ALL_CANONICAL))


_BODY_TIER: Dict[str, int] = {}
for _name in ALL_SUPPORTED_BODIES:
    _cls = _BODY_CLASS.get(_name, "outer")
    _BODY_TIER[_name] = {
        "luminary": 0,
        "personal": 0,
        "social": 1,
        "outer": 2,
        "centaur": 2,
        "asteroid": 2,
        "tno": 3,
        "point": 1,
    }.get(_cls, 2)


_TIER_STEP_MULT = {0: 1.0, 1: 1.5, 2: 2.5, 3: 3.5}


def body_priority(name: str) -> int:
    """Return an integer tier ranking for scanning priority (lower is faster)."""

    canonical = canonical_name(name)
    return _BODY_TIER.get(canonical, 2)


def step_multiplier(name: str) -> float:
    """Return the cadence multiplier for ``name`` based on its tier."""

    return _TIER_STEP_MULT.get(body_priority(name), 2.5)

