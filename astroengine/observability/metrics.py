"""Prometheus metric definitions shared across AstroEngine components."""

from __future__ import annotations

from typing import Iterable

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, REGISTRY

__all__ = [
    "ASPECT_COMPUTE_DURATION",
    "COMPUTE_ERRORS",
    "DIRECTION_COMPUTE_DURATION",
    "EPHEMERIS_BODY_COMPUTE_DURATION",
    "EPHEMERIS_CACHE_HITS",
    "EPHEMERIS_CACHE_MISSES",
    "EPHEMERIS_CACHE_COMPUTE_DURATION",
    "EPHEMERIS_SWE_CACHE_HIT_RATIO",
    "ensure_metrics_registered",
]


ASPECT_COMPUTE_DURATION = Histogram(
    "aspect_compute_duration_seconds",
    "Duration of progressed and directed aspect computations.",
    ("method",),
    registry=None,
)


DIRECTION_COMPUTE_DURATION = Histogram(
    "direction_compute_duration_seconds",
    "Duration of direction timeline calculations.",
    ("method",),
    registry=None,
)


EPHEMERIS_BODY_COMPUTE_DURATION = Histogram(
    "ephemeris_body_compute_duration_seconds",
    "Duration of Swiss ephemeris body position lookups.",
    ("adapter", "operation"),
    registry=None,
)

EPHEMERIS_CACHE_HITS = Counter(
    "ephemeris_cache_hits_total",
    "Total ephemeris cache hits served from in-memory adapters.",
    ("adapter",),
    registry=None,
)

EPHEMERIS_CACHE_MISSES = Counter(
    "ephemeris_cache_misses_total",
    "Total ephemeris cache misses that required backend computation.",
    ("adapter",),
    registry=None,
)

EPHEMERIS_CACHE_COMPUTE_DURATION = Histogram(
    "ephemeris_compute_duration_seconds",
    "Duration of ephemeris backend computations.",
    ("adapter", "body"),
    registry=None,
)

EPHEMERIS_SWE_CACHE_HIT_RATIO = Gauge(
    "ephemeris_core_cache_hit_ratio",
    "Instantaneous hit ratio of the low-level swe_calc cache.",
    registry=None,
)


COMPUTE_ERRORS = Counter(
    "astroengine_compute_errors_total",
    "Count of runtime failures across compute-heavy routines.",
    ("component", "error"),
    registry=None,
)


def _iter_metrics() -> Iterable[Counter | Gauge | Histogram]:
    yield ASPECT_COMPUTE_DURATION
    yield DIRECTION_COMPUTE_DURATION
    yield EPHEMERIS_BODY_COMPUTE_DURATION
    yield EPHEMERIS_CACHE_HITS
    yield EPHEMERIS_CACHE_MISSES
    yield EPHEMERIS_CACHE_COMPUTE_DURATION
    yield EPHEMERIS_SWE_CACHE_HIT_RATIO
    yield COMPUTE_ERRORS


def ensure_metrics_registered(
    registry: CollectorRegistry | None = None,
) -> None:
    """Register shared metrics with ``registry`` if not already present."""

    target = registry or REGISTRY
    for metric in _iter_metrics():
        try:
            target.register(metric)
        except ValueError:
            # Ignore duplicate registrations; Prometheus raises when a metric name
            # already exists in the target registry.
            continue
