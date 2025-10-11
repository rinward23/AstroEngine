from __future__ import annotations

from prometheus_client import CollectorRegistry

from astroengine.observability.metrics import (
    PROVIDER_CACHE_HITS,
    PROVIDER_FAILURES,
    PROVIDER_QUERIES,
    PROVIDER_REGISTRATIONS,
    PROVIDER_REGISTRY_ACTIVE,
    ensure_metrics_registered,
    get_provider_metrics,
    register_provider_metrics,
)


def _assert_sample(
    registry: CollectorRegistry, metric: str, labels: dict[str, str]
) -> float:
    value = registry.get_sample_value(metric, labels)
    assert value is not None
    return value


def test_register_provider_metrics_tracks_version_state() -> None:
    registry = CollectorRegistry()
    ensure_metrics_registered(registry)

    register_provider_metrics("test_provider_metrics", version="1.0.0")

    assert (
        _assert_sample(
            registry,
            PROVIDER_REGISTRATIONS._name,  # type: ignore[attr-defined]
            {"provider_id": "test_provider_metrics", "version": "1.0.0"},
        )
        == 1.0
    )
    assert (
        _assert_sample(
            registry,
            PROVIDER_REGISTRY_ACTIVE._name,  # type: ignore[attr-defined]
            {"provider_id": "test_provider_metrics", "version": "1.0.0"},
        )
        == 1.0
    )

    register_provider_metrics("test_provider_metrics", version="2.0.0")

    assert (
        _assert_sample(
            registry,
            PROVIDER_REGISTRATIONS._name,  # type: ignore[attr-defined]
            {"provider_id": "test_provider_metrics", "version": "2.0.0"},
        )
        == 1.0
    )
    assert (
        _assert_sample(
            registry,
            PROVIDER_REGISTRY_ACTIVE._name,  # type: ignore[attr-defined]
            {"provider_id": "test_provider_metrics", "version": "1.0.0"},
        )
        == 0.0
    )
    assert (
        _assert_sample(
            registry,
            PROVIDER_REGISTRY_ACTIVE._name,  # type: ignore[attr-defined]
            {"provider_id": "test_provider_metrics", "version": "2.0.0"},
        )
        == 1.0
    )

    recorder = get_provider_metrics("test_provider_metrics")
    recorder.record_query("position")
    recorder.record_cache_hit()
    recorder.record_failure("timeout")

    assert (
        _assert_sample(
            registry,
            PROVIDER_QUERIES._name,  # type: ignore[attr-defined]
            {"provider_id": "test_provider_metrics", "call": "position"},
        )
        == 1.0
    )
    assert (
        _assert_sample(
            registry,
            PROVIDER_CACHE_HITS._name,  # type: ignore[attr-defined]
            {"provider_id": "test_provider_metrics"},
        )
        == 1.0
    )
    assert (
        _assert_sample(
            registry,
            PROVIDER_FAILURES._name,  # type: ignore[attr-defined]
            {"provider_id": "test_provider_metrics", "error_code": "timeout"},
        )
        == 1.0
    )
