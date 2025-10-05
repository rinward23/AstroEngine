"""Prometheus metric definitions shared across AstroEngine components."""

from __future__ import annotations

from typing import Iterable

from prometheus_client import CollectorRegistry, Counter, Histogram, REGISTRY

__all__ = [
    "EPHEMERIS_CACHE_HITS",
    "EPHEMERIS_CACHE_MISSES",
    "EPHEMERIS_CACHE_COMPUTE_DURATION",
    "EPHEMERIS_BODY_COMPUTE_DURATION",
    "ASPECT_COMPUTE_DURATION",
    "DIRECTION_COMPUTE_DURATION",
    "COMPUTE_ERRORS",
    "ensure_metrics_registered",
]

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

EPHEMERIS_BODY_COMPUTE_DURATION = Histogram(
    "ephemeris_body_compute_duration_seconds",
    "Duration of Swiss Ephemeris body computations.",
    ("adapter", "operation"),
    registry=None,
)

ASPECT_COMPUTE_DURATION = Histogram(
    "aspect_compute_duration_seconds",
    "Duration of aspect detection runs.",
    ("method",),
    registry=None,
)

DIRECTION_COMPUTE_DURATION = Histogram(
    "direction_compute_duration_seconds",
    "Duration of direction computation runs.",
    ("method",),
    registry=None,
)

COMPUTE_ERRORS = Counter(
    "astroengine_compute_errors_total",
    "Total compute failures labelled by component and error type.",
    ("component", "error"),
    registry=None,
)


def _iter_metrics() -> Iterable[Counter | Histogram]:
    yield EPHEMERIS_CACHE_HITS
    yield EPHEMERIS_CACHE_MISSES
    yield EPHEMERIS_CACHE_COMPUTE_DURATION
    yield EPHEMERIS_BODY_COMPUTE_DURATION
    yield ASPECT_COMPUTE_DURATION
    yield DIRECTION_COMPUTE_DURATION
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
