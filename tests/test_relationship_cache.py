from __future__ import annotations

import time

import pandas as pd
import pytest

from astroengine.cache.relationship import (
    RelationshipResponseCache,
    canonicalize_composite_payload,
    canonicalize_davison_payload,
    canonicalize_synastry_payload,
)
from astroengine.cache.relationship.layer import CacheEntry


def test_synastry_canonicalization_stable():
    payload_a = canonicalize_synastry_payload(
        {"Sun": 10.0, "Moon": 20.0},
        {"Mars": 180.0, "Venus": 120.0},
        ["trine", "square", "trine"],
        {"per_aspect": {"square": 6.0, "trine": 5.0}},
    )
    payload_b = canonicalize_synastry_payload(
        {"Moon": 20.000000001, "Sun": 370.0},
        {"Venus": -240.0, "Mars": 540.0},
        ["square", "trine"],
        {"per_aspect": {"trine": 5.0, "square": 6.0}},
    )
    assert payload_a.digest == payload_b.digest


@pytest.mark.parametrize(
    "factory",
    [
        lambda: canonicalize_composite_payload(
            {"Sun": 12.0},
            {"Sun": 48.0},
            ["Sun", "Moon"],
        ),
        lambda: canonicalize_davison_payload(
            ["Sun"],
            dt_a=pd.Timestamp("2025-01-01T00:00:00Z").to_pydatetime(),
            dt_b=pd.Timestamp("2025-01-02T00:00:00Z").to_pydatetime(),
            lat_a=10.0,
            lon_a=-70.0,
            lat_b=11.0,
            lon_b=-71.0,
        ),
    ],
)
def test_composite_and_davison_keys(factory):
    first = factory()
    second = factory()
    assert first.digest == second.digest


def test_relationship_response_cache_lru_only():
    cache = RelationshipResponseCache("syn", ttl_seconds=60, redis_client=None, lru_maxsize=8, compression=False)
    key = "syn:v1:test-key"
    entry = CacheEntry(body={"ok": True}, status_code=200, headers={}, created_at=time.time())
    cache.set(key, entry)
    outcome = cache.get(key)
    assert outcome.entry is not None
    assert outcome.source == "lru"
    assert outcome.entry.body == {"ok": True}


def test_relationship_response_cache_singleflight(monkeypatch):
    cache = RelationshipResponseCache("syn", ttl_seconds=60, redis_client=None, lru_maxsize=8, compression=False)
    key = "syn:v1:compute"
    calls = 0

    def compute():
        nonlocal calls
        calls += 1
        return CacheEntry(body={"value": calls}, status_code=200, headers={}, created_at=time.time())

    outcome = cache.with_singleflight(key, compute)
    assert outcome.entry is not None
    assert outcome.entry.body["value"] == 1
    assert calls == 1
    # second invocation should hit LRU
    second = cache.get(key)
    assert second.entry is not None
    assert second.entry.body["value"] == 1
    assert second.source == "lru"

