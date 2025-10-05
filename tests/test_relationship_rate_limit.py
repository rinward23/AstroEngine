"""Unit tests for the relationship API rate limiter."""

from __future__ import annotations

import asyncio

import pytest

from app.relationship_api.rate_limit import RateLimiter


class Clock:
    def __init__(self, initial: float = 0.0) -> None:
        self.value = initial

    def advance(self, seconds: float) -> None:
        self.value += seconds

    def __call__(self) -> float:
        return self.value


def test_token_bucket_refills_after_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    limiter = RateLimiter(limit_per_minute=2, redis_url=None)
    clock = Clock(0.0)
    monkeypatch.setattr("app.relationship_api.rate_limit.time.time", clock)

    async def _exercise() -> None:
        first = await limiter.check("ip")
        second = await limiter.check("ip")
        third = await limiter.check("ip")

        assert first.allowed is True
        assert second.allowed is True
        assert third.allowed is False
        assert third.reset_seconds >= 30

        clock.advance(31)
        fourth = await limiter.check("ip")
        assert fourth.allowed is True

    asyncio.run(_exercise())
