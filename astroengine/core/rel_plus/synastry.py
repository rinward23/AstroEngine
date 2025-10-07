"""Synastry helpers for inter-chart aspect detection."""

from __future__ import annotations

import os
import threading
from collections.abc import Iterable

from cachetools import TTLCache

from astroengine.cache.relationship import canonicalize_synastry_payload
from astroengine.core.aspects_plus.harmonics import BASE_ASPECTS
from astroengine.core.aspects_plus.matcher import angular_sep_deg
from astroengine.core.aspects_plus.orb_policy import orb_limit

EPS = 1e-9

_MEMO_CACHE = TTLCache(
    maxsize=int(os.getenv("SYN_HITS_MEMO_MAX", "2048")),
    ttl=int(os.getenv("SYN_HITS_MEMO_TTL", str(24 * 60 * 60))),
)
_MEMO_LOCK = threading.Lock()


def _memoize_hits(key: str, hits: list[dict]) -> list[dict]:
    encoded: tuple[tuple[tuple[str, object], ...], ...] = tuple(
        tuple(sorted(hit.items())) for hit in hits
    )
    with _MEMO_LOCK:
        _MEMO_CACHE[key] = encoded
    return [dict(item) for item in encoded]


def _get_memoized(key: str) -> list[dict] | None:
    with _MEMO_LOCK:
        cached = _MEMO_CACHE.get(key)
    if cached is None:
        return None
    return [dict(item) for item in cached]


def clear_synastry_memoization() -> None:
    """Reset the internal synastry memoization cache."""
    with _MEMO_LOCK:
        _MEMO_CACHE.clear()


def _best_aspect_for_delta(
    a_name: str,
    b_name: str,
    delta: float,
    aspects: Iterable[str],
    policy: dict,
) -> dict | None:
    best: dict | None = None
    for asp in aspects:
        key = asp.lower()
        angle = BASE_ASPECTS.get(key)
        if angle is None:
            continue
        orb = abs(delta - angle)
        limit = orb_limit(a_name, b_name, key, policy)
        if orb <= limit + EPS:
            candidate = {
                "a_obj": a_name,
                "b_obj": b_name,
                "aspect": key,
                "angle": float(angle),
                "delta": float(delta),
                "orb": float(orb),
                "orb_limit": float(limit),
            }
            if best is None or candidate["orb"] < best["orb"]:
                best = candidate
    return best


def synastry_interaspects(
    pos_a: dict[str, float],
    pos_b: dict[str, float],
    aspects: Iterable[str],
    policy: dict,
    weights: dict | None = None,
    gamma: float | None = None,
    node_policy: object | None = None,
) -> list[dict]:
    """Return best inter-aspect matches for each A×B pair within the orb policy."""
    memo_key = canonicalize_synastry_payload(
        pos_a,
        pos_b,
        aspects,
        policy,
        weights=weights,
        gamma=gamma,
        node_policy=node_policy,
    ).digest
    cached = _get_memoized(memo_key)
    if cached is not None:
        return cached
    hits: list[dict] = []
    for a_name, a_lon in pos_a.items():
        for b_name, b_lon in pos_b.items():
            delta = angular_sep_deg(a_lon, b_lon)
            match = _best_aspect_for_delta(a_name, b_name, delta, aspects, policy)
            if match:
                hits.append(match)
    hits.sort(key=lambda h: (h["orb"], h["a_obj"], h["b_obj"]))
    return _memoize_hits(memo_key, hits)


def synastry_grid(hits: list[dict]) -> dict[str, dict[str, int]]:
    """Build a grid of counts per A-object × B-object using best aspects only."""
    grid: dict[str, dict[str, int]] = {}
    for hit in hits:
        a_name = hit["a_obj"]
        b_name = hit["b_obj"]
        row = grid.setdefault(a_name, {})
        row[b_name] = row.get(b_name, 0) + 1
    return grid
