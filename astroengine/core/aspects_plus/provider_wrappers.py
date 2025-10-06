from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from astroengine.core.common.cache import TTLCache

PositionProvider = Callable[[datetime], dict[str, float]]


def _bucket_ts(ts: datetime, resolution_minutes: int) -> datetime:
    ts = ts.astimezone(UTC)
    minutes = (ts.minute // resolution_minutes) * resolution_minutes
    return ts.replace(minute=0, second=0, microsecond=0) + timedelta(minutes=minutes)


def cached_position_provider(
    provider: PositionProvider,
    resolution_minutes: int = 5,
    ttl_seconds: float = 600.0,
    maxsize: int = 4096,
) -> PositionProvider:
    """Wrap a position provider with bucketed timestamp caching.

    - Buckets timestamps to `resolution_minutes` to increase hit rate.
    - Caches the full positions mapping for that bucket.
    """
    cache: TTLCache[tuple, dict[str, float]] = TTLCache(maxsize=maxsize)

    def inner(ts: datetime) -> dict[str, float]:
        bucket = _bucket_ts(ts, resolution_minutes)
        key = (bucket.year, bucket.month, bucket.day, bucket.hour, bucket.minute)
        val = cache.get(key)
        if val is not None:
            return val
        res = provider(ts)
        cache.set(key, res, ttl_seconds)
        return res

    # expose cache for testing
    inner._cache = cache  # type: ignore[attr-defined]
    inner._resolution_minutes = resolution_minutes  # type: ignore[attr-defined]
    return inner
