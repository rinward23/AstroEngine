from __future__ import annotations

import os
import threading
from typing import Any, Dict, Iterable, List, Optional, Tuple

from cachetools import TTLCache

from astroengine.cache.relationship import canonicalize_synastry_payload
from astroengine.core.aspects_plus.matcher import match_pair_prepared
from astroengine.core.aspects_plus.orb_policy import PreparedOrbPolicy, prepare_policy


_MEMO_CACHE = TTLCache(
    maxsize=int(os.getenv("SYN_HITS_MEMO_MAX", "2048")),
    ttl=int(os.getenv("SYN_HITS_MEMO_TTL", str(24 * 60 * 60))),
)
_MEMO_LOCK = threading.Lock()


def _memoize_hits(key: str, hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    encoded: Tuple[Tuple[Tuple[str, Any], ...], ...] = tuple(
        tuple(sorted(hit.items())) for hit in hits
    )
    with _MEMO_LOCK:
        _MEMO_CACHE[key] = encoded
    return [dict(item) for item in encoded]


def _get_memoized(key: str) -> Optional[List[Dict[str, Any]]]:
    with _MEMO_LOCK:
        cached = _MEMO_CACHE.get(key)
    if cached is None:
        return None
    return [dict(item) for item in cached]


def clear_synastry_memoization() -> None:
    """Expose a hook for tests to reset memoized synastry results."""
    with _MEMO_LOCK:
        _MEMO_CACHE.clear()


def synastry_interaspects(
    pos_a: Dict[str, float],
    pos_b: Dict[str, float],
    aspects: Iterable[str],
    policy: Dict[str, Any],
    weights: Optional[Dict[str, Any]] = None,
    gamma: Optional[float] = None,
    node_policy: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """Return best aspect matches for each A↔B pair."""

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

    prepared_policy: PreparedOrbPolicy = prepare_policy(policy)
    aspects_list = list(aspects)
    hits: List[Dict[str, Any]] = []
    append_hit = hits.append
    for a_name, lon_a in pos_a.items():
        if lon_a is None:
            continue
        lon_a_f = float(lon_a)
        for b_name, lon_b in pos_b.items():
            if lon_b is None:
                continue
            lon_b_f = float(lon_b)
            match = match_pair_prepared(
                a_name,
                b_name,
                lon_a_f,
                lon_b_f,
                aspects_list,
                prepared_policy,
            )
            if not match:
                continue
            append_hit(
                {
                    "a_obj": match["a"],
                    "b_obj": match["b"],
                    "aspect": match["aspect"],
                    "angle": float(match["angle"]),
                    "delta": float(match["delta"]),
                    "orb": float(match["orb"]),
                    "orb_limit": float(match["orb_limit"]),
                }
            )
    hits.sort(key=lambda h: (h["a_obj"], h["b_obj"], h["orb"], h["aspect"]))
    return _memoize_hits(memo_key, hits)


def synastry_grid(hits: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    """Build a count grid keyed by (A object → B object)."""

    grid: Dict[str, Dict[str, int]] = {}
    for hit in hits:
        a_name = hit["a_obj"]
        b_name = hit["b_obj"]
        row = grid.setdefault(a_name, {})
        row[b_name] = row.get(b_name, 0) + 1
    return grid
