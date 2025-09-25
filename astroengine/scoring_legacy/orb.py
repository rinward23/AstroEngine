"""Orb calculation helpers driven by the repository's policy JSON."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache, lru_cache

__all__ = ["DEFAULT_ASPECTS", "OrbCalculator", "AspectPolicy"]

DEFAULT_ASPECTS = (0, 60, 90, 120, 180)

_ASPECT_NAME_BY_ANGLE = {
    0: "conjunction",
    60: "sextile",
    90: "square",
    120: "trine",
    150: "quincunx",
    180: "opposition",
}

_BODY_CLASSIFICATION = {
    "sun": "luminaries",
    "moon": "luminaries",
    "mercury": "inner",
    "venus": "inner",
    "mars": "inner",
    "jupiter": "outer",
    "saturn": "outer",
    "uranus": "outer",
    "neptune": "outer",
    "pluto": "outer",
    "chiron": "asteroids",
    "ceres": "asteroids",
    "pallas": "asteroids",
    "juno": "asteroids",
    "vesta": "asteroids",
    "north_node": "asteroids",
    "south_node": "asteroids",
}


from ..infrastructure.paths import schemas_dir


@dataclass(frozen=True)
class AspectPolicy:
    """In-memory representation of a single aspect entry."""

    name: str
    category: str
    base_orb: float
    profile_overrides: Mapping[str, float]


@lru_cache(maxsize=1)
def _load_policy() -> Mapping[str, object]:
    path = schemas_dir() / "orbs_policy.json"
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@cache
def _aspect_policy(name: str) -> AspectPolicy:
    policy = _load_policy()["aspects"][name]
    return AspectPolicy(
        name=name,
        category=policy["category"],
        base_orb=float(policy["base_orb"]),
        profile_overrides={
            k: float(v) for k, v in policy.get("profile_overrides", {}).items()
        },
    )


class OrbCalculator:
    """Compute orb allowances based on policy definitions."""

    def __init__(self, policy: Mapping[str, object] | None = None) -> None:
        self._policy = policy or _load_policy()

    @staticmethod
    def aspect_name_for(angle: int) -> str:
        angle_int = int(round(angle))
        if angle_int not in _ASPECT_NAME_BY_ANGLE:
            raise KeyError(f"Unsupported aspect angle: {angle_int}")
        return _ASPECT_NAME_BY_ANGLE[angle_int]

    def orb_for(
        self,
        body_a: str,
        body_b: str,
        angle: int,
        *,
        profile: str = "standard",
    ) -> float:
        """Return the orb allowance for the supplied pair of bodies."""

        aspect_name = self.aspect_name_for(angle)
        aspect = _aspect_policy(aspect_name)

        profile_key = profile if profile in self._policy["profiles"] else "standard"
        profile_spec = self._policy["profiles"][profile_key]
        multipliers = profile_spec.get("multipliers", {})
        base_orb = aspect.profile_overrides.get(profile_key, aspect.base_orb)
        modifier_a = self._body_multiplier(body_a, multipliers)
        modifier_b = self._body_multiplier(body_b, multipliers)
        return base_orb * (modifier_a + modifier_b) / 2.0

    @staticmethod
    def _body_multiplier(body: str, multipliers: Mapping[str, float]) -> float:
        classification = _BODY_CLASSIFICATION.get(body.lower())
        if not classification:
            return 1.0
        return float(multipliers.get(classification, 1.0))
