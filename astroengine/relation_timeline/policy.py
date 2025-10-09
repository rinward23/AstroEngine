"""Policy constants and helpers for relationship timeline scoring."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

__all__ = [
    "DEFAULT_TRANSITERS",
    "DEFAULT_TARGETS",
    "DEFAULT_ASPECTS",
    "BASE_ORBS",
    "ASPECT_CAPS",
    "ASPECT_FAMILY",
    "ASPECT_WEIGHTS",
    "TRANSITER_WEIGHTS",
    "TARGET_FAMILY",
    "TARGET_WEIGHTS",
    "SCORE_NORMALIZER",
    "SERIES_SAMPLE_HOURS",
]


DEFAULT_TRANSITERS: tuple[str, ...] = ("Venus", "Mars", "Jupiter", "Saturn")
"""Transit-capable bodies supported in the MVP implementation."""


DEFAULT_TARGETS: tuple[str, ...] = (
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
    "Chiron",
    "Node",
)
"""Default Composite/Davison targets receiving aspects from transiters."""


DEFAULT_ASPECTS: tuple[int, ...] = (0, 60, 90, 120, 180)
"""Major aspects scanned by default for performance reasons."""


BASE_ORBS: Mapping[str, float] = {
    "Venus": 3.0,
    "Mars": 2.5,
    "Jupiter": 2.0,
    "Saturn": 2.0,
}
"""Base orb allowances keyed by transiting body."""


ASPECT_CAPS: Mapping[int, float] = {
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
}
"""Aspect-specific orb caps in degrees."""


ASPECT_FAMILY: Mapping[int, str] = {
    0: "neutral",
    30: "harmonious",
    45: "challenging",
    60: "harmonious",
    72: "harmonious",
    90: "challenging",
    120: "harmonious",
    135: "challenging",
    144: "harmonious",
    150: "challenging",
    180: "challenging",
}
"""Family classification guiding aspect weighting."""


ASPECT_WEIGHTS: Mapping[str, float] = {
    "harmonious": 1.0,
    "challenging": 1.1,
    "neutral": 0.95,
}
"""Per-family multipliers applied to timeline scores."""


TRANSITER_WEIGHTS: Mapping[str, float] = {
    "Venus": 1.0,
    "Mars": 1.1,
    "Jupiter": 1.0,
    "Saturn": 1.2,
}
"""Relative influence multipliers per transiting body."""


TARGET_FAMILY: Mapping[str, str] = {
    "Sun": "luminary",
    "Moon": "luminary",
    "Mercury": "personal",
    "Venus": "personal",
    "Mars": "personal",
    "Jupiter": "social",
    "Saturn": "social",
    "Uranus": "outer",
    "Neptune": "outer",
    "Pluto": "outer",
    "Chiron": "points",
    "Node": "points",
}
"""Map of composite bodies into scoring families."""


TARGET_WEIGHTS: Mapping[str, float] = {
    "luminary": 1.3,
    "personal": 1.1,
    "social": 1.0,
    "outer": 0.85,
    "points": 0.8,
}
"""Weight multipliers keyed by target family."""


SCORE_NORMALIZER: float = 60.0
"""Calibration factor keeping event scores in a human-scaled range."""


SERIES_SAMPLE_HOURS: int = 6
"""Step in hours when optional severity series sampling is requested."""


@dataclass(frozen=True)
class OrbPolicy:
    """Computed orb policy for a transiter / aspect combination."""

    base: float
    cap: float

    @property
    def effective(self) -> float:
        return min(self.base, self.cap)
