from __future__ import annotations

from typing import Any, Dict, Iterable, List

from astroengine.core.aspects_plus.matcher import match_pair


def synastry_interaspects(
    pos_a: Dict[str, float],
    pos_b: Dict[str, float],
    aspects: Iterable[str],
    policy: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Return best aspect matches for each A↔B pair."""

    hits: List[Dict[str, Any]] = []
    for a_name, lon_a in pos_a.items():
        if lon_a is None:
            continue
        for b_name, lon_b in pos_b.items():
            if lon_b is None:
                continue
            match = match_pair(a_name, b_name, float(lon_a), float(lon_b), aspects, policy)
            if not match:
                continue
            hits.append(
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
    return hits


def synastry_grid(hits: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    """Build a count grid keyed by (A object → B object)."""

    grid: Dict[str, Dict[str, int]] = {}
    for hit in hits:
        a_name = hit["a_obj"]
        b_name = hit["b_obj"]
        row = grid.setdefault(a_name, {})
        row[b_name] = row.get(b_name, 0) + 1
    return grid
