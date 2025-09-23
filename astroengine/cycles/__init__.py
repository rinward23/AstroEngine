"""Cycles and age analytics namespace for :mod:`astroengine`."""

from __future__ import annotations

from .ages import AgeBoundary, AgeSample, AgeSeries, compute_age_series, derive_age_boundaries
from .generational import (
    DEFAULT_OUTER_ASPECTS,
    DEFAULT_OUTER_BODIES,
    CyclePairSample,
    CycleTimeline,
    WavePoint,
    WaveSeries,
    neptune_pluto_wave,
    outer_cycle_timeline,
)

__all__ = [
    "DEFAULT_OUTER_ASPECTS",
    "DEFAULT_OUTER_BODIES",
    "CyclePairSample",
    "CycleTimeline",
    "WavePoint",
    "WaveSeries",
    "AgeSample",
    "AgeSeries",
    "AgeBoundary",
    "outer_cycle_timeline",
    "neptune_pluto_wave",
    "compute_age_series",
    "derive_age_boundaries",
]

