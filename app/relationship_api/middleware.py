"""API middleware stack (request context, body limits, rate limiting)."""

from __future__ import annotations

import hashlib
from logging import LoggerAdapter
from time import perf_counter
from typing import Callable
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.requests import ClientDisconnect
from starlette.types import ASGIApp

from .config import ServiceSettings
from .models import ApiError
from .rate_limit import RateLimiter
from .telemetry import get_logger


class RequestLogger(LoggerAdapter):
    def process(self, msg, kwargs):  # type: ignore[override]
        kwargs.setdefault("extra", {})
        kwargs["extra"].setdefault("request_id", self.extra.get("request_id", "-"))
        return msg, kwargs


class BodyLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI, max_bytes: int) -> None:
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next: Callable):  # type: ignore[override]
        header_len = request.headers.get("content-length")
        if header_len and int(header_len) > self.max_bytes:
            payload = ApiError(code="REQUEST_TOO_LARGE", message="Payload exceeds limit").model_dump()
            return JSONResponse(status_code=413, content=payload)
        # Starlette caches the body after it is first read; no need to store it on the request.
        body = await request.body()
        if len(body) > self.max_bytes:
            payload = ApiError(code="REQUEST_TOO_LARGE", message="Payload exceeds limit").model_dump()
            return JSONResponse(status_code=413, content=payload)
        return await call_next(request)


class RequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI, rate_limiter: RateLimiter | None) -> None:
        super().__init__(app)
        self.rate_limiter = rate_limiter

    async def dispatch(self, request: Request, call_next: Callable):  # type: ignore[override]
        request_id = request.headers.get("x-request-id") or uuid4().hex
        adapter = RequestLogger(get_logger(), {"request_id": request_id})
        request.state.logger = adapter
        request.state.request_id = request_id
        start = perf_counter()
        adapter.info(
            "request.start",
            extra={
                "method": request.method,
                "path": request.url.path,
                "length": request.headers.get("content-length", "0"),
            },
        )
        rate_headers: dict[str, str] | None = None
        if self.rate_limiter is not None:
            identity = (
                request.client.host if request.client and request.client.host else "anonymous"
            )
            trust_proxy = getattr(request.app.state, "trust_proxy", False)
            if trust_proxy:
                x_real = request.headers.get("x-real-ip")
                xff = request.headers.get("x-forwarded-for")
                if x_real:
                    identity = x_real.strip()
                elif xff:
                    identity = xff.split(",")[0].strip()
            result = await self.rate_limiter.check(identity)
            rate_headers = {
                "X-RateLimit-Limit": str(self.rate_limiter.limit),
                "X-RateLimit-Remaining": str(max(0, result.remaining)),
                "X-RateLimit-Reset": str(result.reset_seconds),
            }
            if not result.allowed:
                adapter.warning("rate.limit.exceeded", extra={"path": request.url.path})
                payload = ApiError(code="rate_limited", message="Too many requests").model_dump()
                headers = {
                    "Retry-After": str(int(result.reset_seconds)),
                    "X-RateLimit-Reason": "token_bucket",
                }
                headers.update(rate_headers)
                headers["X-Request-ID"] = request_id
                return JSONResponse(status_code=429, content=payload, headers=headers)
        try:
            response = await call_next(request)
        except ClientDisconnect:
            adapter.warning("request.client_disconnect", extra={"path": request.url.path})
            raise
        except Exception as exc:
            adapter.exception("request.error", extra={"error": str(exc)})
            raise
        finally:
            duration_ms = (perf_counter() - start) * 1000.0
            adapter.info(
                "request.end",
                extra={"path": request.url.path, "duration_ms": f"{duration_ms:.2f}"},
            )
        response.headers.setdefault("X-Request-ID", request_id)
        if rate_headers:
            for key, value in rate_headers.items():
                response.headers.setdefault(key, value)
        return response


class ETagMiddleware(BaseHTTPMiddleware):
    """Attach weak ETag headers for cacheable GET responses."""

    async def dispatch(self, request: Request, call_next: Callable):  # type: ignore[override]
        response = await call_next(request)

        if request.method != "GET" or not (200 <= response.status_code < 300):
            return response

        if any(header.lower() == "etag" for header in response.headers.keys()):
            return response

        body: bytes
        if hasattr(response, "body_iterator") and response.body_iterator is not None:
            chunks = [chunk async for chunk in response.body_iterator]
            body = b"".join(chunks)
            response.body_iterator = iter([body])
        else:
            # ``Response.body`` may be ``None`` for streaming responses; coerce to bytes.
            body = response.body or b""
            response.body = body

        tag = hashlib.sha1(body).hexdigest()
        etag = f'W/"{tag}"'
        response.headers["ETag"] = etag

        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers={"ETag": etag})

        return response


def install_middleware(app: FastAPI, settings: ServiceSettings) -> None:
    app.add_middleware(GZipMiddleware, minimum_size=settings.gzip_minimum_size)
    app.add_middleware(
        SecurityHeadersMiddleware,
        enable_hsts=settings.enable_hsts and settings.tls_terminates_upstream,
        hsts_max_age=settings.hsts_max_age,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origin_list()),
        allow_credentials=False,
        allow_methods=list(settings.cors_allow_methods),
        allow_headers=list(settings.cors_allow_headers),
    )
    rate_limiter = RateLimiter(settings.rate_limit_per_minute, settings.redis_url)
    app.add_middleware(BodyLimitMiddleware, max_bytes=settings.request_max_bytes)
    app.add_middleware(RequestContextMiddleware, rate_limiter=rate_limiter)
    app.add_middleware(ETagMiddleware)


__all__ = ["install_middleware", "RequestLogger", "ETagMiddleware"]
