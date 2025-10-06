"""Orb and weighting policies for the synastry matrix engine."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from astroengine.core.bodies import ALL_SUPPORTED_BODIES, body_class, canonical_name

__all__ = [
    "OrbPolicy",
    "Weights",
    "HARMONIOUS_ASPECTS",
    "CHALLENGING_ASPECTS",
    "NEUTRAL_ASPECTS",
    "ASPECT_FAMILY_MAP",
    "DEFAULT_ORB_POLICY",
    "DEFAULT_WEIGHTS",
    "DEFAULT_ASPECT_SET",
]


HARMONIOUS_ASPECTS = frozenset({60, 120, 72, 144})
CHALLENGING_ASPECTS = frozenset({90, 180, 45, 135, 150})
NEUTRAL_ASPECTS = frozenset({0, 30})
DEFAULT_ASPECT_SET = tuple(sorted(HARMONIOUS_ASPECTS | CHALLENGING_ASPECTS | NEUTRAL_ASPECTS))


def _normalize_aspect(value: int | float) -> int:
    aspect = int(round(float(value)))
    if aspect not in {0, 30, 45, 60, 72, 90, 120, 135, 144, 150, 180}:
        raise ValueError(f"Unsupported aspect angle: {value!r}")
    return aspect


ASPECT_FAMILY_MAP: dict[int, str] = {}
for _angle in DEFAULT_ASPECT_SET:
    if _angle in HARMONIOUS_ASPECTS:
        ASPECT_FAMILY_MAP[_angle] = "harmonious"
    elif _angle in CHALLENGING_ASPECTS:
        ASPECT_FAMILY_MAP[_angle] = "challenging"
    else:
        ASPECT_FAMILY_MAP[_angle] = "neutral"


@dataclass(frozen=True)
class OrbPolicy:
    """Encapsulates base orb allowances and per-aspect caps."""

    base_orb_by_body: Mapping[str, float] = field(default_factory=dict)
    cap_by_aspect: Mapping[int, float] = field(default_factory=dict)
    default_base_orb: float = 5.0
    default_aspect_cap: float = 5.0

    def __post_init__(self) -> None:
        normalized_pairs: dict[frozenset[str], float] = {}
        normalized_single: dict[str, float] = {}
        for key, value in dict(self.base_orb_by_body).items():
            if not isinstance(key, str):
                continue
            raw = key.strip()
            if "|" in raw:
                parts = tuple(sorted(canonical_name(part) for part in raw.split("|")))
                normalized_pairs[frozenset(parts)] = float(value)
            else:
                normalized_single[canonical_name(raw)] = float(value)
        object.__setattr__(self, "_pair_orbs", normalized_pairs)
        object.__setattr__(self, "_single_orbs", normalized_single)
        caps = {int(_normalize_aspect(angle)): float(limit) for angle, limit in self.cap_by_aspect.items()}
        object.__setattr__(self, "_caps", caps)

    def base_orb(self, body_a: str, body_b: str) -> float:
        """Return the base orb allowance for ``(body_a, body_b)`` before aspect caps."""

        name_a = canonical_name(body_a)
        name_b = canonical_name(body_b)
        pair_key = frozenset({name_a, name_b})
        if pair_key in self._pair_orbs:
            return self._pair_orbs[pair_key]
        values = [
            self._single_orbs.get(name_a),
            self._single_orbs.get(name_b),
        ]
        present = [value for value in values if value is not None]
        if present:
            return float(min(present))
        return float(self.default_base_orb)

    def cap(self, aspect: int) -> float:
        """Return the maximum orb allowance for ``aspect``."""

        return float(self._caps.get(_normalize_aspect(aspect), self.default_aspect_cap))

    def effective_orb(self, body_a: str, body_b: str, aspect: int) -> float:
        """Return the effective orb for the pair under the policy."""

        base = self.base_orb(body_a, body_b)
        cap = self.cap(aspect)
        return float(base if base < cap else cap)


@dataclass(frozen=True)
class Weights:
    """Weight multipliers used during scoring aggregation."""

    aspect_family: Mapping[str, float]
    body_family: Mapping[str, float]
    conjunction_sign: float = 1.0

    def aspect_weight(self, family: str) -> float:
        return float(self.aspect_family.get(family, 1.0))

    def body_weight(self, family: str) -> float:
        return float(self.body_family.get(family, 1.0))


_BODY_FAMILY_ORBS = {
    "luminary": 8.0,
    "personal": 6.0,
    "social": 5.0,
    "outer": 5.0,
    "centaur": 5.0,
    "asteroid": 5.0,
    "tno": 5.0,
    "point": 5.0,
}


def _default_base_orbs() -> dict[str, float]:
    mapping: dict[str, float] = {}
    for name in ALL_SUPPORTED_BODIES:
        cls = body_class(name)
        mapping[name] = _BODY_FAMILY_ORBS.get(cls, 5.0)
    # Provide nicer title-case aliases for common luminaries/planets
    pretty_aliases = {
        "Sun": "sun",
        "Moon": "moon",
        "Mercury": "mercury",
        "Venus": "venus",
        "Mars": "mars",
        "Jupiter": "jupiter",
        "Saturn": "saturn",
        "Uranus": "uranus",
        "Neptune": "neptune",
        "Pluto": "pluto",
        "Chiron": "chiron",
        "True Node": "true_node",
        "Node": "mean_node",
    }
    for alias, canonical in pretty_aliases.items():
        mapping[alias] = mapping.get(canonical, 5.0)
    return mapping


DEFAULT_ORB_POLICY = OrbPolicy(
    base_orb_by_body=_default_base_orbs(),
    cap_by_aspect={
        0: 8.0,
        30: 2.0,
        45: 2.0,
        60: 4.0,
        72: 1.5,
        90: 6.0,
        120: 6.0,
        135: 2.0,
        144: 1.5,
        150: 2.0,
        180: 8.0,
    },
    default_base_orb=5.0,
    default_aspect_cap=4.0,
)

DEFAULT_WEIGHTS = Weights(
    aspect_family={
        "harmonious": 1.0,
        "challenging": 1.0,
        "neutral": 0.8,
    },
    body_family={
        "luminary": 1.2,
        "personal": 1.0,
        "social": 0.8,
        "outer": 0.8,
        "points": 0.9,
    },
    conjunction_sign=1.0,
)

