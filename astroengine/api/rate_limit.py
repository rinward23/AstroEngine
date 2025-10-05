"""Lightweight rate limiting helpers for public API endpoints."""

from __future__ import annotations

import asyncio
import math
import time
from collections import deque
from dataclasses import dataclass
from typing import Awaitable, Callable, Deque, Dict

from fastapi import HTTPException, Request, Response, status


@dataclass
class RateLimitStatus:
    """Result describing whether a request is allowed."""

    allowed: bool
    remaining: int
    reset_seconds: float


class SimpleRateLimiter:
    """In-memory token bucket keyed by caller identity."""

    def __init__(self, limit: int, window_seconds: float) -> None:
        self.limit = int(limit)
        self.window = float(window_seconds)
        self._hits: Dict[str, Deque[float]] = {}
        self._lock = asyncio.Lock()

    async def check(self, identity: str) -> RateLimitStatus:
        """Record a request for ``identity`` and return the quota status."""

        async with self._lock:
            now = time.monotonic()
            bucket = self._hits.get(identity)
            if bucket is None:
                bucket = deque()
                self._hits[identity] = bucket

            while bucket and now - bucket[0] >= self.window:
                bucket.popleft()

            if not bucket:
                # Release memory for identities that have aged out.
                self._hits.pop(identity, None)
                bucket = deque()
                self._hits[identity] = bucket

            if len(bucket) >= self.limit:
                reset = self.window - (now - bucket[0])
                return RateLimitStatus(False, 0, max(reset, 0.0))

            bucket.append(now)
            remaining = max(0, self.limit - len(bucket))
            reset = self.window - (now - bucket[0]) if bucket else self.window
            return RateLimitStatus(True, remaining, max(reset, 0.0))


def _resolve_identity(request: Request) -> str:
    user_headers = [
        "x-api-user",
        "x-user-id",
        "x-user",
    ]
    for header in user_headers:
        value = request.headers.get(header)
        if value:
            return value.strip()

    trust_proxy = getattr(request.app.state, "trust_proxy", False)
    if trust_proxy:
        x_real = request.headers.get("x-real-ip")
        if x_real:
            return x_real.strip()
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()

    client = request.client
    if client and client.host:
        return client.host
    return "anonymous"


def _limiter_registry(request: Request) -> Dict[str, SimpleRateLimiter]:
    registry = getattr(request.app.state, "_simple_rate_limiters", None)
    if registry is None:
        registry = {}
        setattr(request.app.state, "_simple_rate_limiters", registry)
    return registry


def _get_limiter(
    request: Request, scope: str, limit: int, window_seconds: int | float
) -> SimpleRateLimiter:
    registry = _limiter_registry(request)
    limiter = registry.get(scope)
    if limiter is None or limiter.limit != limit or limiter.window != float(window_seconds):
        limiter = SimpleRateLimiter(limit=limit, window_seconds=float(window_seconds))
        registry[scope] = limiter
    return limiter


def heavy_endpoint_rate_limiter(
    scope: str,
    *,
    limit: int = 10,
    window_seconds: int = 60,
    message: str | None = None,
) -> Callable[[Request, Response], Awaitable[None]]:
    """Return a dependency enforcing a simple rate limit for ``scope``."""

    friendly = message or "This endpoint is receiving a high volume of requests."

    async def _dependency(request: Request, response: Response) -> None:
        limiter = _get_limiter(request, scope, limit, window_seconds)
        identity = _resolve_identity(request)
        status_info = await limiter.check(identity)
        reset_seconds = max(0, math.ceil(status_info.reset_seconds))
        headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(max(0, status_info.remaining)),
            "X-RateLimit-Reset": str(reset_seconds),
        }

        if not status_info.allowed:
            detail = {
                "code": "rate_limited",
                "message": f"{friendly} Please try again in {reset_seconds} seconds.",
            }
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=detail,
                headers={**headers, "Retry-After": str(reset_seconds)},
            )

        for key, value in headers.items():
            response.headers.setdefault(key, value)

    return _dependency


__all__ = [
    "RateLimitStatus",
    "SimpleRateLimiter",
    "heavy_endpoint_rate_limiter",
]

