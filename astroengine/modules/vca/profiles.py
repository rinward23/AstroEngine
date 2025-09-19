"""Domain scoring profiles for AstroEngine."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class DomainScoringProfile:
    """Severity multipliers applied per domain after geometric severity is computed."""

    name: str
    domain_multipliers: Mapping[str, float]


VCA_DOMAIN_PROFILES = {
    "vca_neutral": DomainScoringProfile(
        name="vca_neutral",
        domain_multipliers={"MIND": 1.0, "BODY": 1.0, "SPIRIT": 1.0},
    ),
    "vca_mind_plus": DomainScoringProfile(
        name="vca_mind_plus",
        domain_multipliers={"MIND": 1.25, "BODY": 1.0, "SPIRIT": 1.0},
    ),
    "vca_body_plus": DomainScoringProfile(
        name="vca_body_plus",
        domain_multipliers={"MIND": 1.0, "BODY": 1.25, "SPIRIT": 1.0},
    ),
    "vca_spirit_plus": DomainScoringProfile(
        name="vca_spirit_plus",
        domain_multipliers={"MIND": 1.0, "BODY": 1.0, "SPIRIT": 1.25},
    ),
}


__all__ = ["DomainScoringProfile", "VCA_DOMAIN_PROFILES"]
