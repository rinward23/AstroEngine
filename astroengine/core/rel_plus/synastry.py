"""Synastry helpers for inter-chart aspect detection."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from astroengine.core.aspects_plus.harmonics import BASE_ASPECTS
from astroengine.core.aspects_plus.matcher import angular_sep_deg
from astroengine.core.aspects_plus.orb_policy import orb_limit

EPS = 1e-9


def _best_aspect_for_delta(
    a_name: str,
    b_name: str,
    delta: float,
    aspects: Iterable[str],
    policy: Dict,
) -> Optional[dict]:
    best: Optional[dict] = None
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
    pos_a: Dict[str, float],
    pos_b: Dict[str, float],
    aspects: Iterable[str],
    policy: Dict,
) -> List[Dict]:
    """Return best inter-aspect matches for each A×B pair within the orb policy."""
    hits: List[Dict] = []
    for a_name, a_lon in pos_a.items():
        for b_name, b_lon in pos_b.items():
            delta = angular_sep_deg(a_lon, b_lon)
            match = _best_aspect_for_delta(a_name, b_name, delta, aspects, policy)
            if match:
                hits.append(match)
    hits.sort(key=lambda h: (h["orb"], h["a_obj"], h["b_obj"]))
    return hits


def synastry_grid(hits: List[Dict]) -> Dict[str, Dict[str, int]]:
    """Build a grid of counts per A-object × B-object using best aspects only."""
    grid: Dict[str, Dict[str, int]] = {}
    for hit in hits:
        a_name = hit["a_obj"]
        b_name = hit["b_obj"]
        row = grid.setdefault(a_name, {})
        row[b_name] = row.get(b_name, 0) + 1
    return grid
