"""Domain scoring profiles for AstroEngine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

# >>> AUTO-GEN BEGIN: VCA Domain Scoring Profile v1.0


@dataclass(frozen=True)
class DomainScoringProfile:
    """Severity multipliers applied per domain after geometric severity is computed."""

    name: str
    domain_multipliers: Mapping[str, float]


# Sensible defaults; teams can add more via profile registry later.
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


# >>> AUTO-GEN END: VCA Domain Scoring Profile v1.0


__all__ = ["DomainScoringProfile", "VCA_DOMAIN_PROFILES"]

