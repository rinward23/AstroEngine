"""Scoring utilities exposed at the package level."""

from __future__ import annotations

from ..core.scoring import compute_domain_factor
from .contact import ScoreInputs, ScoreResult, compute_score
from .dignity import DignityRecord, load_dignities, lookup_dignities
from .orb import DEFAULT_ASPECTS, OrbCalculator

__all__ = [
    "compute_domain_factor",
    "compute_score",
    "ScoreInputs",
    "ScoreResult",
    "DEFAULT_ASPECTS",
    "OrbCalculator",
    "DignityRecord",
    "load_dignities",
    "lookup_dignities",
]
