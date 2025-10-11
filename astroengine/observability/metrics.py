"""Prometheus metric definitions shared across AstroEngine components."""

from __future__ import annotations

from collections.abc import Iterable

from prometheus_client import REGISTRY, CollectorRegistry, Counter, Gauge, Histogram

__all__ = [
    "ASPECT_COMPUTE_DURATION",
    "COMPUTE_ERRORS",
    "DIRECTION_COMPUTE_DURATION",
    "EPHEMERIS_BODY_COMPUTE_DURATION",
    "EPHEMERIS_CACHE_COMPUTE_DURATION",
    "EPHEMERIS_CACHE_HITS",
    "EPHEMERIS_CACHE_MISSES",
    "EPHEMERIS_SWE_CACHE_HIT_RATIO",
    "PROVIDER_CACHE_HITS",
    "PROVIDER_FAILURES",
    "PROVIDER_QUERIES",
    "PROVIDER_REGISTRATIONS",
    "PROVIDER_REGISTRY_ACTIVE",
    "ProviderMetricRecorder",
    "ensure_metrics_registered",
    "get_provider_metrics",
    "register_provider_metrics",
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
    yield PROVIDER_REGISTRATIONS
    yield PROVIDER_REGISTRY_ACTIVE
    yield PROVIDER_QUERIES
    yield PROVIDER_CACHE_HITS
    yield PROVIDER_FAILURES


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
PROVIDER_REGISTRATIONS = Counter(
    "astroengine_provider_registrations_total",
    "Total registration events recorded for ephemeris providers.",
    ("provider_id", "version"),
    registry=None,
)


PROVIDER_REGISTRY_ACTIVE = Gauge(
    "astroengine_provider_registry_active",
    "Number of active providers currently registered in the registry.",
    ("provider_id", "version"),
    registry=None,
)


PROVIDER_QUERIES = Counter(
    "astroengine_provider_queries_total",
    "Total provider query calls issued across implementations.",
    ("provider_id", "call"),
    registry=None,
)


PROVIDER_CACHE_HITS = Counter(
    "astroengine_provider_cache_hits_total",
    "Total cache hits served by provider implementations.",
    ("provider_id",),
    registry=None,
)


PROVIDER_FAILURES = Counter(
    "astroengine_provider_failures_total",
    "Total provider call failures grouped by error code.",
    ("provider_id", "error_code"),
    registry=None,
)


class ProviderMetricRecorder:
    """Helper bound to a provider for consistent metric emission."""

    __slots__ = ("provider_id", "version")

    def __init__(self, provider_id: str, version: str) -> None:
        self.provider_id = provider_id
        self.version = version

    def record_query(self, call: str) -> None:
        """Increment the provider query counter for ``call``."""

        PROVIDER_QUERIES.labels(
            provider_id=self.provider_id, call=_normalise_label(call)
        ).inc()

    def record_cache_hit(self) -> None:
        """Increment the provider cache hit counter."""

        PROVIDER_CACHE_HITS.labels(provider_id=self.provider_id).inc()

    def record_failure(self, error_code: str) -> None:
        """Increment the provider failure counter for ``error_code``."""

        PROVIDER_FAILURES.labels(
            provider_id=self.provider_id, error_code=_normalise_label(error_code)
        ).inc()


_PROVIDER_RECORDERS: dict[str, ProviderMetricRecorder] = {}
_PROVIDER_VERSIONS: dict[str, str] = {}


def _normalise_label(value: str | object) -> str:
    return str(value)


def register_provider_metrics(
    provider_id: str,
    *,
    version: str | None = None,
) -> ProviderMetricRecorder:
    """Register provider metric recorders and update lifecycle counters."""

    normalised_version = _normalise_label(version or "unknown")
    PROVIDER_REGISTRATIONS.labels(
        provider_id=provider_id, version=normalised_version
    ).inc()

    previous_version = _PROVIDER_VERSIONS.get(provider_id)
    if previous_version is not None and previous_version != normalised_version:
        PROVIDER_REGISTRY_ACTIVE.labels(
            provider_id=provider_id, version=previous_version
        ).set(0)

    PROVIDER_REGISTRY_ACTIVE.labels(
        provider_id=provider_id, version=normalised_version
    ).set(1)
    _PROVIDER_VERSIONS[provider_id] = normalised_version

    recorder = ProviderMetricRecorder(provider_id, normalised_version)
    _PROVIDER_RECORDERS[provider_id] = recorder
    return recorder


def get_provider_metrics(provider_id: str) -> ProviderMetricRecorder:
    """Return the metric recorder registered for ``provider_id``."""

    try:
        return _PROVIDER_RECORDERS[provider_id]
    except KeyError as exc:  # pragma: no cover - defensive guard
        raise KeyError(f"provider metrics not initialised for '{provider_id}'") from exc
