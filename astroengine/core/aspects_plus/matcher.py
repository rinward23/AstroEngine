
from __future__ import annotations

from collections.abc import Callable, Iterable
from itertools import combinations
from typing import Any

from .harmonics import BASE_ASPECTS
from .orb_policy import PreparedOrbPolicy, orb_limit, orb_limit_prepared

EPS = 1e-9


def _norm360(x: float) -> float:
    v = x % 360.0
    return v + 360.0 if v < 0 else v


def angular_sep_deg(lon_a: float, lon_b: float) -> float:
    """Return the absolute circular separation in degrees within [0, 180]."""
    a = _norm360(lon_a)
    b = _norm360(lon_b)
    d = abs(a - b)
    if d > 180.0:
        d = 360.0 - d
    return d


def _match_for_delta(
    a_name: str,
    b_name: str,
    delta: float,
    aspects: Iterable[str],
    policy: Any,
    *,
    limit_fn: Callable[[str, str, str, Any], float] = orb_limit,
):
    best = None
    for asp in aspects:
        key = asp.lower()
        angle = BASE_ASPECTS.get(key)
        if angle is None:
            continue
        orb = abs(delta - angle)
        limit = limit_fn(a_name, b_name, key, policy)
        if orb <= limit + EPS:
            cand = {
                "a": a_name,
                "b": b_name,
                "aspect": key,
                "delta": delta,
                "orb": orb,
                "orb_limit": float(limit),
                "angle": float(angle),
            }
            if best is None or cand["orb"] < best["orb"]:
                best = cand
    return best


def match_pair(
    a_name: str,
    b_name: str,
    lon_a: float,
    lon_b: float,
    aspects: Iterable[str],
    policy: dict,
):
    """Match a single pair. Returns best match dict or None."""
    delta = angular_sep_deg(float(lon_a), float(lon_b))
    return _match_for_delta(a_name, b_name, delta, aspects, policy)


def match_pair_prepared(
    a_name: str,
    b_name: str,
    lon_a: float,
    lon_b: float,
    aspects: Iterable[str],
    policy: PreparedOrbPolicy,
):
    """Fast-path pair matcher that reuses a prepared policy."""

    delta = angular_sep_deg(float(lon_a), float(lon_b))
    return _match_for_delta(
        a_name,
        b_name,
        delta,
        aspects,
        policy,
        limit_fn=orb_limit_prepared,
    )


def match_all(
    positions: dict[str, float],
    aspects: Iterable[str],
    policy: dict,
    pairs: Iterable[tuple[str, str]] | None = None,
) -> list[dict]:
    """Match across all pairs in positions or a restricted `pairs` list.

    Args:
        positions: mapping object_name → ecliptic longitude degrees [0..360).
        aspects: iterable of aspect names to consider.
        policy: OrbPolicy dict.
        pairs: optional list of (A,B) tuples; if None, generate all unordered pairs.
    """
    names = list(positions.keys())
    if pairs is None:
        pairs_iter = combinations(names, 2)
    else:
        pairs_iter = pairs

    out: list[dict] = []
    for a_name, b_name in pairs_iter:
        if a_name not in positions or b_name not in positions:
            continue
        m = match_pair(a_name, b_name, positions[a_name], positions[b_name], aspects, policy)
        if m:
            out.append(m)
    # sort by smallest orb then by time-order left to higher layers
    out.sort(key=lambda x: (x["orb"], x["a"], x["b"]))
    return out
