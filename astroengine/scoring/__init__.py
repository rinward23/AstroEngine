"""Scoring utilities exposed at the package level."""

from __future__ import annotations

from dataclasses import dataclass

from ..core.scoring import compute_domain_factor
from .dignity import DignityRecord, load_dignities, lookup_dignities
from .orb import DEFAULT_ASPECTS, OrbCalculator


@dataclass
class ScoreInputs:
    """Inputs describing a transit contact for severity scoring."""

    kind: str
    orb_abs_deg: float
    orb_allow_deg: float
    moving: str
    target: str
    applying_or_separating: str


@dataclass
class ScoreResult:
    """Resulting base score and supporting magnitude details."""

    score: float
    falloff_ratio: float


def compute_score(inputs: ScoreInputs) -> ScoreResult:
    """Return a normalized (0..1) score based on orb proportion.

    The falloff is quadratic relative to the allowed orb. Applying events receive a
    modest uplift to ensure temporal prioritization without inventing synthetic
    values; all numbers derive directly from the geometric relationship between
    the actual orb and configured allowance.
    """

    allow = max(float(inputs.orb_allow_deg), 1e-6)
    ratio = min(max(float(inputs.orb_abs_deg) / allow, 0.0), 1.0)
    base = 1.0 - ratio ** 2
    if inputs.applying_or_separating.lower() == "applying":
        base *= 1.05
    else:
        base *= 0.95
    return ScoreResult(score=max(0.0, min(base, 1.0)), falloff_ratio=ratio)


__all__ = [
    "compute_domain_factor",
    "DEFAULT_ASPECTS",
    "OrbCalculator",
    "DignityRecord",
    "load_dignities",
    "lookup_dignities",
    "ScoreInputs",
    "ScoreResult",
    "compute_score",
]
