"""Rate limiting utilities backed by Redis with in-memory fallback."""

from __future__ import annotations

from dataclasses import dataclass
import asyncio
import time
from typing import Dict

from .telemetry import get_logger

try:  # pragma: no cover - optional dependency
    from redis.asyncio import Redis
    from redis.exceptions import (
        ConnectionError as RedisConnectionError,
        RedisError,
        TimeoutError as RedisTimeoutError,
    )
except ImportError:  # pragma: no cover - redis optional
    Redis = None  # type: ignore[assignment]

    class RedisError(Exception):  # type: ignore[dead-code]
        """Fallback RedisError for environments without redis-py."""

    class RedisConnectionError(RedisError):  # type: ignore[dead-code]
        """Fallback connection error."""

    class RedisTimeoutError(asyncio.TimeoutError):  # type: ignore[dead-code]
        """Fallback timeout error."""

    get_logger().info(
        "redis client unavailable",
        extra={"err_code": "REDIS_IMPORT", "request_id": "-"},
        exc_info=True,
    )


@dataclass(slots=True)
class RateLimitResult:
    allowed: bool
    remaining: int
    reset_seconds: int


class RateLimiter:
    """Minute-based sliding window rate limiter."""

    def __init__(self, limit_per_minute: int, redis_url: str | None) -> None:
        self.limit = max(1, int(limit_per_minute))
        self._redis_url = redis_url
        self._redis: Redis | None = None
        self._memory: Dict[str, tuple[int, int]] = {}
        if redis_url and Redis is not None:
            try:
                self._redis = Redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
            except (RedisConnectionError, RedisError, OSError, ValueError) as exc:  # pragma: no cover - connection errors handled at runtime
                get_logger().error(
                    "rate limiter redis setup failed",
                    extra={
                        "error": str(exc),
                        "request_id": "-",
                        "err_code": "REDIS_CONN",
                    },
                    exc_info=True,
                )
                self._redis = None

    async def check(self, identity: str) -> RateLimitResult:
        now = int(time.time())
        window_reset = 60 - (now % 60)
        if self._redis is not None:
            key = f"rl:{identity}:{now // 60}"
            try:
                pipe = self._redis.pipeline()
                pipe.incr(key)
                pipe.expire(key, 120)
                count, _ = await pipe.execute()
            except (RedisTimeoutError, asyncio.TimeoutError) as exc:  # pragma: no cover - redis runtime failure
                get_logger().warning(
                    "rate limiter redis timeout",
                    extra={
                        "error": str(exc),
                        "request_id": "-",
                        "err_code": "REDIS_TIMEOUT",
                    },
                    exc_info=True,
                )
            except (RedisError, OSError) as exc:  # pragma: no cover - redis runtime failure
                get_logger().error(
                    "rate limiter redis failed",
                    extra={
                        "error": str(exc),
                        "request_id": "-",
                        "err_code": "REDIS_ERROR",
                    },
                    exc_info=True,
                )
            else:
                count_int = int(count)
                remaining = max(0, self.limit - count_int)
                return RateLimitResult(
                    allowed=count_int <= self.limit,
                    remaining=remaining,
                    reset_seconds=window_reset,
                )
        # Fallback memory limiter
        count, expiry = self._memory.get(identity, (0, now + 60))
        if expiry <= now:
            count = 0
            expiry = now + 60
        count += 1
        self._memory[identity] = (count, expiry)
        remaining = max(0, self.limit - count)
        return RateLimitResult(
            allowed=count <= self.limit,
            remaining=remaining,
            reset_seconds=max(1, expiry - now),
        )


__all__ = ["RateLimiter", "RateLimitResult"]
