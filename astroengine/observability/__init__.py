"""Runtime observability primitives for AstroEngine modules."""

from __future__ import annotations

from .metrics import (
    EPHEMERIS_CACHE_COMPUTE_DURATION,
    EPHEMERIS_CACHE_HITS,
    EPHEMERIS_CACHE_MISSES,
    EPHEMERIS_SWE_CACHE_HIT_RATIO,
    ensure_metrics_registered,
)

__all__ = [
    "EPHEMERIS_CACHE_HITS",
    "EPHEMERIS_CACHE_MISSES",
    "EPHEMERIS_CACHE_COMPUTE_DURATION",
    "EPHEMERIS_SWE_CACHE_HIT_RATIO",
    "ensure_metrics_registered",
]
