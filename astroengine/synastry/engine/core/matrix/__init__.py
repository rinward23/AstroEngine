"""Synastry matrix core exports."""

from __future__ import annotations

from .detector import detect_hits
from .grid import build_grid
from .models import ChartPositions, EclipticPosition, GridCell, Hit, Overlay, OverlayLine, Scores
from .overlay import make_overlay
from .policy import (
    ASPECT_FAMILY_MAP,
    CHALLENGING_ASPECTS,
    DEFAULT_ASPECT_SET,
    DEFAULT_ORB_POLICY,
    DEFAULT_WEIGHTS,
    HARMONIOUS_ASPECTS,
    NEUTRAL_ASPECTS,
    OrbPolicy,
    Weights,
)
from .scoring import compute_scores

__all__ = [
    "ChartPositions",
    "EclipticPosition",
    "Hit",
    "GridCell",
    "Overlay",
    "OverlayLine",
    "Scores",
    "OrbPolicy",
    "Weights",
    "DEFAULT_ORB_POLICY",
    "DEFAULT_WEIGHTS",
    "DEFAULT_ASPECT_SET",
    "HARMONIOUS_ASPECTS",
    "CHALLENGING_ASPECTS",
    "NEUTRAL_ASPECTS",
    "ASPECT_FAMILY_MAP",
    "detect_hits",
    "build_grid",
    "make_overlay",
    "compute_scores",
]
