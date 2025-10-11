"""Runtime observability primitives for AstroEngine modules."""

from __future__ import annotations

from .doctor import DoctorCheck, run_system_doctor
from .metrics import (
    ASPECT_COMPUTE_DURATION,
    COMPUTE_ERRORS,
    DIRECTION_COMPUTE_DURATION,
    EPHEMERIS_BODY_COMPUTE_DURATION,
    EPHEMERIS_CACHE_COMPUTE_DURATION,
    EPHEMERIS_CACHE_HITS,
    EPHEMERIS_CACHE_MISSES,
    EPHEMERIS_SWE_CACHE_HIT_RATIO,
    PROVIDER_CACHE_HITS,
    PROVIDER_FAILURES,
    PROVIDER_QUERIES,
    PROVIDER_REGISTRATIONS,
    PROVIDER_REGISTRY_ACTIVE,
    ProviderMetricRecorder,
    ensure_metrics_registered,
    get_provider_metrics,
    register_provider_metrics,
)

__all__ = [
    "ASPECT_COMPUTE_DURATION",
    "COMPUTE_ERRORS",
    "DIRECTION_COMPUTE_DURATION",
    "EPHEMERIS_BODY_COMPUTE_DURATION",
    "EPHEMERIS_CACHE_HITS",
    "EPHEMERIS_CACHE_MISSES",
    "EPHEMERIS_CACHE_COMPUTE_DURATION",
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
    "DoctorCheck",
    "run_system_doctor",
]
