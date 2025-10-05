"""Lightweight observability helpers for the public FastAPI app."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Callable
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from prometheus_client import Counter, Histogram, make_asgi_app
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

from astroengine.observability import ensure_metrics_registered
from app.telemetry import resolve_observability_config, setup_tracing

try:  # pragma: no cover - optional dependency
    from opentelemetry import trace as _otel_trace
except Exception:  # pragma: no cover - otel not installed
    _otel_trace = None


_LOGGER = logging.getLogger("astroengine.app")


class JSONLogFormatter(logging.Formatter):
    """Serialize log records as JSON with contextual metadata."""

    _RESERVED_KEYS = {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
    }

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401 - brief docstring above
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)

        for key, value in record.__dict__.items():
            if key in self._RESERVED_KEYS:
                continue
            payload[key] = value

        payload.update(_trace_log_fields())

        return json.dumps(payload, default=str)


class RequestContextLoggerAdapter(logging.LoggerAdapter):
    """Ensure middleware logs consistently include request context."""

    def process(self, msg: str, kwargs: Any) -> tuple[str, dict[str, Any]]:
        extra = kwargs.setdefault("extra", {})
        for key, value in self.extra.items():
            extra.setdefault(key, value)
        for key, value in _trace_log_fields().items():
            extra.setdefault(key, value)
        return msg, kwargs


def _configure_logging() -> None:
    """Install a JSON formatter on the root logger once per process."""

    if getattr(_configure_logging, "_configured", False):  # type: ignore[attr-defined]
        return

    handler = logging.StreamHandler()
    handler.setFormatter(JSONLogFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    root.setLevel(getattr(logging, level_name, logging.INFO))

    # Quiet overly verbose default handlers when structured logs are enabled.
    logging.getLogger("uvicorn.error").handlers.clear()
    logging.getLogger("uvicorn.access").handlers.clear()
    logging.getLogger("uvicorn").propagate = True

    _configure_logging._configured = True  # type: ignore[attr-defined]


def _configure_opentelemetry(app: FastAPI) -> None:
    """Configure OpenTelemetry exporters and instrumentation."""

    if getattr(app.state, "_otel_configured", False):
        return

    cfg = resolve_observability_config(app)
    app.state._observability_cfg = cfg

    if cfg is None or not cfg.otel_enabled:
        app.state._otel_configured = True
        return

    try:  # pragma: no cover - instrumentation exercised in integration tests
        from opentelemetry import metrics
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
            OTLPMetricExporter,
        )
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk.resources import Resource
    except ImportError:  # pragma: no cover - optional dependency
        _LOGGER.warning(
            "observability.opentelemetry_missing",
            extra={"err_code": "OTEL_DEPENDENCY_MISSING"},
        )
        app.state._otel_configured = True
        return

    setup_tracing(app, sampling_ratio=cfg.sampling_ratio, enabled=cfg.otel_enabled)

    resource = Resource.create({"service.name": "astroengine-api"})
    metric_reader = PeriodicExportingMetricReader(OTLPMetricExporter())
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    app.state._otel_configured = True


REQUEST_COUNT = Counter(
    "astroengine_requests_total",
    "Total HTTP requests processed by the AstroEngine API.",
    ("method", "path", "status"),
)
REQUEST_LATENCY = Histogram(
    "astroengine_request_latency_seconds",
    "Latency of HTTP requests processed by the AstroEngine API.",
    ("method", "path"),
)


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    if route and getattr(route, "path_format", None):
        return route.path_format  # type: ignore[return-value]
    return request.url.path


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Ensure every request has a stable request ID for logging."""

    async def dispatch(self, request: Request, call_next: Callable):  # type: ignore[override]
        request_id = request.headers.get("x-request-id") or uuid4().hex
        request.state.request_id = request_id
        user_agent = request.headers.get("user-agent", "")
        logger = RequestContextLoggerAdapter(
            _LOGGER, {"request_id": request_id, "user_agent": user_agent}
        )
        request.state.logger = logger
        logger.info(
            "request.start",
            extra={
                "method": request.method,
                "path": request.url.path,
                "length": request.headers.get("content-length", "0"),
                "user_agent": user_agent,
                **_trace_log_fields(),
            },
        )
        start = perf_counter()
        try:
            response = await call_next(request)
        except HTTPException as exc:  # pragma: no cover - defensive logging
            logger.warning(
                "request.http_error",
                extra={
                    "error": str(exc.detail),
                    "status": exc.status_code,
                    "err_code": "HTTP_ERROR",
                },
                exc_info=True,
            )
            raise
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception(
                "request.error",
                extra={"error": str(exc), "err_code": "UNEXPECTED"},
            )
            raise
        finally:
            duration_ms = (perf_counter() - start) * 1000.0
            status_code = (
                getattr(response, "status_code", None)
                if "response" in locals()
                else None
            )
            logger.info(
                "request.end",
                extra={
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                    "status_code": status_code,
                    **_trace_log_fields(),
                },
            )
        response.headers.setdefault("X-Request-ID", request_id)
        trace_meta = _trace_log_fields()
        trace_id = trace_meta.get("trace_id")
        if trace_id:
            response.headers.setdefault("X-Trace-ID", trace_id)
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Emit Prometheus metrics about request outcomes."""

    async def dispatch(self, request: Request, call_next: Callable):  # type: ignore[override]
        start = perf_counter()
        path_template = _route_template(request)
        method = request.method
        try:
            response = await call_next(request)
        except HTTPException as exc:
            duration = perf_counter() - start
            REQUEST_COUNT.labels(method=method, path=path_template, status=str(exc.status_code)).inc()
            REQUEST_LATENCY.labels(method=method, path=path_template).observe(duration)
            logger = getattr(request.state, "logger", _LOGGER)
            logger.warning(
                "metrics.http_error",
                extra={
                    "err_code": "HTTP_ERROR",
                    "status": exc.status_code,
                    "method": method,
                    "path": path_template,
                },
                exc_info=True,
            )
            raise
        except Exception:
            duration = perf_counter() - start
            REQUEST_COUNT.labels(method=method, path=path_template, status="500").inc()
            REQUEST_LATENCY.labels(method=method, path=path_template).observe(duration)
            logger = getattr(request.state, "logger", _LOGGER)
            logger.exception(
                "metrics.unexpected_error",
                extra={
                    "err_code": "UNEXPECTED",
                    "method": method,
                    "path": path_template,
                },
            )
            raise
        duration = perf_counter() - start
        REQUEST_COUNT.labels(
            method=method,
            path=path_template,
            status=str(response.status_code),
        ).inc()
        REQUEST_LATENCY.labels(method=method, path=path_template).observe(duration)
        return response


def configure_observability(app: FastAPI) -> None:
    """Install middleware and the /metrics endpoint."""

    _configure_logging()
    _configure_opentelemetry(app)
    app.add_middleware(GZipMiddleware)
    environment = os.getenv("ENV", "dev")
    allow_origins = ["*"] if environment == "dev" else []
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(MetricsMiddleware)
    ensure_metrics_registered()
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)


__all__ = ["configure_observability", "RequestIdMiddleware", "MetricsMiddleware"]

def _trace_log_fields() -> dict[str, str]:
    """Return trace correlation identifiers when OpenTelemetry is active."""

    if _otel_trace is None:
        return {}

    span = _otel_trace.get_current_span()
    if not span:
        return {}

    context = span.get_span_context()
    if context is None:
        return {}

    is_valid_attr = getattr(context, "is_valid", None)
    if callable(is_valid_attr):
        is_valid = bool(is_valid_attr())
    else:
        is_valid = bool(is_valid_attr)
    if not is_valid:
        return {}

    trace_id = format(context.trace_id, "032x")
    span_id = format(context.span_id, "016x")
    return {"trace_id": trace_id, "span_id": span_id}
