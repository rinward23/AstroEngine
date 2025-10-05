"""OpenTelemetry tracing helpers for the AstroEngine API."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import FastAPI

_LOGGER = logging.getLogger("astroengine.telemetry")


def setup_tracing(
    app: FastAPI,
    sqlalchemy_engine: Optional[object] = None,
    service_name: str = "astroengine-api",
) -> None:
    """Configure OpenTelemetry tracing instrumentation if available."""

    sql_configured_flag = "_otel_sqlalchemy_instrumented"
    tracing_configured_flag = "_otel_tracing_configured"

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
        provider = TracerProvider(resource=resource)
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
