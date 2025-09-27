import time

from astroengine.core.common.cache import TTLCache, ttl_cache


def test_ttlcache_basic_set_get_expire():
    c = TTLCache(maxsize=4)
    c.set("a", 1, ttl_seconds=0.2)
    assert c.get("a") == 1
    time.sleep(0.25)
    assert c.get("a") is None


def test_ttl_cache_decorator():
    calls = {"n": 0}

    @ttl_cache(0.5)
    def f(x):
        calls["n"] += 1
        return x * 2

    assert f(2) == 4
    assert f(2) == 4
    assert calls["n"] == 1  # cached
    time.sleep(0.6)
    assert f(2) == 4
    assert calls["n"] == 2  # expired
