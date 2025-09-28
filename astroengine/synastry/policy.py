"""Policies for synastry midpoint scanning."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from astroengine.core.bodies import body_class

__all__ = [
    "MidpointPolicy",
    "family_for_body",
]


_CLASS_TO_FAMILY = MappingProxyType(
    {
        "luminary": "luminary",
        "personal": "personal",
        "social": "social",
        "outer": "outer",
        "point": "points",
        "centaur": "points",
        "asteroid": "points",
        "tno": "outer",
    }
)


DEFAULT_ORB_BASES = MappingProxyType(
    {
        "luminary": 2.0,
        "personal": 1.5,
        "social": 1.2,
        "outer": 1.2,
        "points": 1.2,
        "other": 1.0,
    }
)


DEFAULT_FAMILY_WEIGHTS = MappingProxyType(
    {
        "luminary": 1.2,
        "personal": 1.0,
        "social": 0.9,
        "outer": 0.8,
        "points": 0.9,
        "other": 0.8,
    }
)


def family_for_body(name: str) -> str:
    """Return the midpoint family bucket for ``name``."""

    cls = body_class(name)
    family = _CLASS_TO_FAMILY.get(cls)
    return family if family is not None else "outer"


@dataclass(frozen=True)
class MidpointPolicy:
    """Configuration knobs for midpoint hit detection."""

    orb_bases: Mapping[str, float] = field(
        default_factory=lambda: DEFAULT_ORB_BASES
    )
    orb_cap: float = 2.0
    probe_family_weights: Mapping[str, float] = field(
        default_factory=lambda: DEFAULT_FAMILY_WEIGHTS
    )
    source_family_weights: Mapping[str, float] = field(
        default_factory=lambda: DEFAULT_FAMILY_WEIGHTS
    )
    severity_gamma: float = 1.0

    def effective_orb(self, body_name: str) -> float:
        """Return the capped orb allowance for ``body_name``."""

        family = family_for_body(body_name)
        base = self.orb_bases.get(family)
        if base is None:
            base = self.orb_bases.get("other", 1.0)
        base = max(0.0, float(base))
        return float(min(self.orb_cap, base)) if self.orb_cap > 0 else base

    def probe_weight(self, body_name: str) -> float:
        """Return the weighting factor for the supplied probe body."""

        family = family_for_body(body_name)
        weight = self.probe_family_weights.get(family)
        if weight is None:
            weight = self.probe_family_weights.get("other", 1.0)
        return float(weight)

    def source_weight(self, body_name: str) -> float:
        """Return the weighting factor for the supplied source body."""

        family = family_for_body(body_name)
        weight = self.source_family_weights.get(family)
        if weight is None:
            weight = self.source_family_weights.get("other", 1.0)
        return float(weight)

