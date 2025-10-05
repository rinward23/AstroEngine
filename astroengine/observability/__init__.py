"""Runtime observability primitives for AstroEngine modules."""

from __future__ import annotations

from .metrics import (
    ASPECT_COMPUTE_DURATION,
    COMPUTE_ERRORS,
    DIRECTION_COMPUTE_DURATION,
    EPHEMERIS_BODY_COMPUTE_DURATION,
    EPHEMERIS_CACHE_COMPUTE_DURATION,
    EPHEMERIS_CACHE_HITS,
    EPHEMERIS_CACHE_MISSES,
    ensure_metrics_registered,
)

__all__ = [
    "ASPECT_COMPUTE_DURATION",
    "COMPUTE_ERRORS",
    "DIRECTION_COMPUTE_DURATION",
    "EPHEMERIS_BODY_COMPUTE_DURATION",
    "EPHEMERIS_CACHE_HITS",
    "EPHEMERIS_CACHE_MISSES",
    "EPHEMERIS_CACHE_COMPUTE_DURATION",
    "ensure_metrics_registered",
]
