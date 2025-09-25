"""Body classification and gating helpers for AstroEngine bodies."""

from __future__ import annotations

from functools import cache
from typing import Dict, Set

__all__ = [
    "ALL_SUPPORTED_BODIES",
    "body_class",
    "body_priority",
    "canonical_name",
    "step_multiplier",
]


# Canonical name -> classification
_BODY_CLASS: Dict[str, str] = {
    # Luminaries & planets
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
    # Dwarf planets / TNOs
    "eris": "tno",
    "haumea": "tno",
    "makemake": "tno",
    "sedna": "tno",
    "quaoar": "tno",
    "orcus": "tno",
    "ixion": "tno",
    # Calculated points
    "mean_lilith": "point",
    "true_lilith": "point",
    "vertex": "point",
    "antivertex": "point",
    "fortune": "point",
    "spirit": "point",
}


# Friendly aliases -> canonical name
_BODY_ALIASES: Dict[str, str] = {
    "north_node": "mean_node",
    "node": "mean_node",
    "nn": "mean_node",
    "sn": "south_node",
    "black_moon_lilith": "mean_lilith",
    "lilith": "mean_lilith",
    "anti-vertex": "antivertex",
    "avx": "antivertex",
    "part_of_fortune": "fortune",
    "pof": "fortune",
}


_ALL_CANONICAL: Set[str] = set(_BODY_CLASS)
ALL_SUPPORTED_BODIES: Set[str] = set(sorted(_ALL_CANONICAL))


# Body priority tiers influence scheduling cadence.
_BODY_TIER: Dict[str, int] = {}
for _name in ALL_SUPPORTED_BODIES:
    _cls = _BODY_CLASS.get(_name, "outer")
    _BODY_TIER[_name] = {
        "luminary": 0,
        "personal": 0,
        "social": 1,
        "point": 1,
        "asteroid": 2,
        "centaur": 2,
        "outer": 2,
        "tno": 3,
    }.get(_cls, 2)


_TIER_STEP_MULT = {0: 1.0, 1: 1.5, 2: 2.5, 3: 3.5}


def canonical_name(name: str | None) -> str:
    """Return the canonical body identifier for ``name``."""

    key = (name or "").strip().lower()
    return _BODY_ALIASES.get(key, key)


@cache
def body_class(name: str | None) -> str:
    """Return the scoring class for the provided body name."""

    if not name:
        return "outer"
    return _BODY_CLASS.get(canonical_name(name), "outer")


def body_priority(name: str | None) -> int:
    """Return the scheduling priority tier for ``name``."""

    return _BODY_TIER.get(canonical_name(name), 2)


def step_multiplier(name: str | None) -> float:
    """Return the cadence multiplier for ``name`` used by scan gating."""

    return _TIER_STEP_MULT.get(body_priority(name), 2.5)

