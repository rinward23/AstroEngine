"""Scoring utilities exposed at the package level."""

from __future__ import annotations

from ..core.scoring import compute_domain_factor
from .contact import (
    ScoreInputs,
    ScoreResult,
    compute_score,
    compute_uncertainty_confidence,
)
from .dignity import DignityRecord, load_dignities, lookup_dignities
from .orb import DEFAULT_ASPECTS, OrbCalculator
from .policy import (
    OrbPolicy,
    SeverityPolicy,
    VisibilityPolicy,
    load_orb_policy,
    load_severity_policy,
    load_visibility_policy,
)
from .tradition import TraditionSpec, get_tradition_spec

__all__ = [
    "compute_domain_factor",
    "compute_score",
    "compute_uncertainty_confidence",
    "ScoreInputs",
    "ScoreResult",
    "DEFAULT_ASPECTS",
    "OrbCalculator",
    "DignityRecord",
    "load_dignities",
    "lookup_dignities",
    "OrbPolicy",
    "SeverityPolicy",
    "VisibilityPolicy",
    "load_orb_policy",
    "load_severity_policy",
    "load_visibility_policy",
    "TraditionSpec",
    "get_tradition_spec",
]
