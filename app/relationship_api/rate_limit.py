"""Rate limiting utilities backed by Redis with in-memory fallback."""

from __future__ import annotations

import asyncio
import math
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .telemetry import get_logger

try:  # pragma: no cover - optional dependency
    from redis.asyncio import Redis
    from redis.exceptions import (
        ConnectionError as RedisConnectionError,
    )
    from redis.exceptions import (
        RedisError,
    )
    from redis.exceptions import (
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
    """Token bucket rate limiter with Redis coordination and in-memory fallback."""

    _SCRIPT = """
    local key = KEYS[1]
    local capacity = tonumber(ARGV[1])
    local refill = tonumber(ARGV[2])
    local now = tonumber(ARGV[3])
    local ttl = tonumber(ARGV[4])

    local bucket = redis.call('HMGET', key, 'tokens', 'timestamp')
    local tokens = capacity
    local last = now
    if bucket[1] then
        tokens = tonumber(bucket[1]) or capacity
    end
    if bucket[2] then
        last = tonumber(bucket[2]) or now
    end

    if last < 0 then
        last = now
    end

    local delta = math.max(0, now - last)
    tokens = math.min(capacity, tokens + delta * refill)

    local allowed = 0
    if tokens >= 1 then
        allowed = 1
        tokens = tokens - 1
    end

    redis.call('HSET', key, 'tokens', tokens, 'timestamp', now)
    redis.call('PEXPIRE', key, ttl)
    return {allowed, tokens}
    """

    if TYPE_CHECKING:  # pragma: no cover - typing helper
        from redis.asyncio.client import Script

    def __init__(self, limit_per_minute: int, redis_url: str | None) -> None:
        self.limit = max(1, int(limit_per_minute))
        self._redis_url = redis_url
        self._redis: Redis | None = None
        self._redis_script: Script | None = None
        self._memory: dict[str, tuple[float, float]] = {}
        self._refill_per_second = self.limit / 60.0
        self._redis_ttl_ms = 120_000
        if redis_url and Redis is not None:
            try:
                self._redis = Redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
                try:
                    self._redis_script = self._redis.register_script(self._SCRIPT)
                except Exception:  # pragma: no cover - script registration fallback
                    self._redis_script = None
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
        now = time.time()
        if self._redis is not None:
            key = f"rl:{identity}"
            try:
                if self._redis_script is not None:
                    allowed, tokens = await self._redis_script(
                        keys=[key],
                        args=[
                            float(self.limit),
                            float(self._refill_per_second),
                            float(now),
                            int(self._redis_ttl_ms),
                        ],
                    )
                else:
                    allowed, tokens = await self._redis.eval(
                        self._SCRIPT,
                        1,
                        key,
                        float(self.limit),
                        float(self._refill_per_second),
                        float(now),
                        int(self._redis_ttl_ms),
                    )
            except (TimeoutError, RedisTimeoutError) as exc:  # pragma: no cover - redis runtime failure
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
                allowed_bool = bool(int(allowed))
                tokens_float = float(tokens)
                remaining = max(0, int(math.floor(tokens_float)))
                reset_seconds = self._compute_reset(tokens_float)
                return RateLimitResult(
                    allowed=allowed_bool,
                    remaining=remaining,
                    reset_seconds=reset_seconds,
                )
        # Fallback memory limiter
        tokens, last = self._memory.get(identity, (float(self.limit), now))
        delta = max(0.0, now - last)
        tokens = min(float(self.limit), tokens + delta * self._refill_per_second)
        allowed = tokens >= 1.0
        if allowed:
            tokens -= 1.0
        self._memory[identity] = (tokens, now)
        remaining = max(0, int(math.floor(tokens)))
        reset_seconds = self._compute_reset(tokens)
        return RateLimitResult(
            allowed=allowed,
            remaining=remaining,
            reset_seconds=reset_seconds,
        )

    def _compute_reset(self, tokens: float) -> int:
        if tokens >= 1.0:
            return 0
        if self._refill_per_second <= 0:
            return 60
        missing = max(0.0, 1.0 - tokens)
        seconds = math.ceil(missing / self._refill_per_second)
        return max(1, int(seconds))


__all__ = ["RateLimiter", "RateLimitResult"]
