"""Ephemeris adapters and helpers exposed by :mod:`astroengine`."""

from __future__ import annotations

from .adapter import (
    EphemerisAdapter,
    EphemerisConfig,
    EphemerisSample,
    ObserverLocation,
    RefinementError,
    TimeScaleContext,
)
from .refinement import (
    SECONDS_PER_DAY,
    RefineResult,
    bracket_root,
    refine_event,
    refine_root,
)
from .support import SupportIssue, filter_supported
from .swisseph_adapter import (
    BodyPosition,

    FixedStarPosition,
    HousePositions,
    RiseTransitResult,

    SwissEphemerisAdapter,
)

__all__ = [
    "EphemerisAdapter",
    "EphemerisConfig",
    "EphemerisSample",
    "ObserverLocation",
    "RefinementError",
    "RefineResult",
    "refine_event",
    "refine_root",
    "bracket_root",
    "SECONDS_PER_DAY",
    "SwissEphemerisAdapter",
    "BodyPosition",
    "HousePositions",
    "FixedStarPosition",
    "RiseTransitResult",

    "TimeScaleContext",
    "SupportIssue",
    "filter_supported",
]
