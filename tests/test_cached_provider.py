from datetime import datetime, timedelta, timezone

from astroengine.core.aspects_plus.provider_wrappers import cached_position_provider


def test_cached_provider_buckets_and_caches():
    calls = {"n": 0}

    def provider(ts):
        calls["n"] += 1
        return {"Sun": 0.0, "Moon": 0.0}

    cached = cached_position_provider(provider, resolution_minutes=5, ttl_seconds=60)

    t0 = datetime(2025, 1, 1, 12, 3, tzinfo=timezone.utc)
    t1 = t0 + timedelta(minutes=1)  # same 5-min bucket
    t2 = t0 + timedelta(minutes=7)  # next bucket

    cached(t0)
    cached(t1)
    cached(t2)

    # provider should have been called twice (two buckets)
    assert calls["n"] == 2
