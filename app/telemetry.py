"""OpenTelemetry tracing helpers for the AstroEngine API."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import FastAPI

from astroengine.runtime_config import runtime_settings

_LOGGER = logging.getLogger("astroengine.telemetry")


if TYPE_CHECKING:  # pragma: no cover - for type checking only
    from astroengine.config.settings import ObservabilityCfg


def resolve_observability_config(app: FastAPI) -> ObservabilityCfg | None:
    """Return the active observability configuration, if available."""

    cached = getattr(app.state, "_observability_cfg", None)
    if cached is not None:
        return cached

    settings = getattr(app.state, "settings", None)
    cfg = getattr(settings, "observability", None) if settings else None
    if cfg is not None:
        return cfg
    try:
        return runtime_settings.persisted().observability
    except Exception as exc:  # pragma: no cover - defensive guard
        _LOGGER.debug(
            "telemetry.settings_load_failed",
            extra={"err_code": "SETTINGS_LOAD_FAILED", "error": str(exc)},
        )
        return None


def setup_tracing(
    app: FastAPI,
    sqlalchemy_engine: object | None = None,
    service_name: str = "astroengine-api",
    sampling_ratio: float | None = None,
    enabled: bool | None = None,
) -> None:
    """Configure OpenTelemetry tracing instrumentation if available."""

    sql_configured_flag = "_otel_sqlalchemy_instrumented"
    tracing_configured_flag = "_otel_tracing_configured"

    cfg = None
    if sampling_ratio is None or enabled is None:
        cfg = resolve_observability_config(app)
    if enabled is None:
        enabled = bool(getattr(cfg, "otel_enabled", False))
    if not enabled:
        return

    if sampling_ratio is None:
        sampling_ratio = getattr(cfg, "sampling_ratio", 1.0)
    sampling_ratio = max(0.0, min(1.0, float(sampling_ratio)))

    if (
        getattr(app.state, tracing_configured_flag, False)
        and (
            not sqlalchemy_engine
            or getattr(app.state, sql_configured_flag, False)
        )
    ):
        return

    try:  # pragma: no cover - optional dependency plumbing
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.requests import RequestsInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
    except ImportError:
        _LOGGER.warning(
            "telemetry.opentelemetry_missing",
            extra={"err_code": "OTEL_DEPENDENCY_MISSING"},
        )
        setattr(app.state, tracing_configured_flag, True)
        if sqlalchemy_engine is not None:
            setattr(app.state, sql_configured_flag, True)
        return

    if not getattr(app.state, tracing_configured_flag, False):
        resource = Resource.create({"service.name": service_name})
        sampler = ParentBased(TraceIdRatioBased(float(sampling_ratio)))
        provider = TracerProvider(resource=resource, sampler=sampler)
        trace.set_tracer_provider(provider)
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        FastAPIInstrumentor.instrument_app(
            app,
            excluded_urls=r"/(metrics|healthz|readyz)",
        )
        RequestsInstrumentor().instrument()
        setattr(app.state, tracing_configured_flag, True)

    if (
        sqlalchemy_engine is not None
        and not getattr(app.state, sql_configured_flag, False)
    ):
        SQLAlchemyInstrumentor().instrument(engine=sqlalchemy_engine)
        setattr(app.state, sql_configured_flag, True)
