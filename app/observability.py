"""Lightweight observability helpers for the public FastAPI app."""

from __future__ import annotations

import logging
import os
from time import perf_counter
from typing import Callable
from uuid import uuid4

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from prometheus_client import Counter, Histogram, make_asgi_app
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware


_LOGGER = logging.getLogger("astroengine.app")


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
        logger = logging.LoggerAdapter(_LOGGER, {"request_id": request_id})
        request.state.logger = logger
        logger.info(
            "request.start",
            extra={
                "method": request.method,
                "path": request.url.path,
                "length": request.headers.get("content-length", "0"),
            },
        )
        start = perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("request.error", extra={"error": str(exc)})
            raise
        finally:
            duration_ms = (perf_counter() - start) * 1000.0
            logger.info(
                "request.end",
                extra={"path": request.url.path, "duration_ms": f"{duration_ms:.2f}"},
            )
        response.headers.setdefault("X-Request-ID", request_id)
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Emit Prometheus metrics about request outcomes."""

    async def dispatch(self, request: Request, call_next: Callable):  # type: ignore[override]
        start = perf_counter()
        path_template = _route_template(request)
        method = request.method
        try:
            response = await call_next(request)
        except Exception:
            duration = perf_counter() - start
            REQUEST_COUNT.labels(method=method, path=path_template, status="500").inc()
            REQUEST_LATENCY.labels(method=method, path=path_template).observe(duration)
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
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)


__all__ = ["configure_observability", "RequestIdMiddleware", "MetricsMiddleware"]

