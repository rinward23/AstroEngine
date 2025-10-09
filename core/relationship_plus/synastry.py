"""Synastry helpers for combining two position sets."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from astroengine.core.aspects_plus.harmonics import BASE_ASPECTS
from astroengine.core.aspects_plus.matcher import angular_sep_deg
from astroengine.core.aspects_plus.orb_policy import orb_limit


@dataclass
class SynastryHit:
    """Container for a single synastry hit."""


    a: str
    b: str
    aspect: str
    angle: float
    delta: float
    orb: float
    limit: float
    severity: float



def _pair_weight(
    weights: Mapping[tuple[str, str], float] | None,
    a: str,
    b: str,
) -> float:
    if not weights:
        return 1.0
    if (a, b) in weights:
        return float(weights[(a, b)])
    if (b, a) in weights:
        return float(weights[(b, a)])
    return 1.0


def _best_aspect(
    a_name: str,
    b_name: str,
    delta: float,
    aspects: Iterable[str],
    policy: Mapping[str, Any],
) -> tuple[str, float, float] | None:
    best: tuple[str, float, float] | None = None
    for asp in aspects:
        key = asp.lower()
        angle = BASE_ASPECTS.get(key)
        if angle is None:
            continue
        limit = float(orb_limit(a_name, b_name, key, policy))
        orb = abs(delta - float(angle))
        if orb <= limit or best is None:
            best = (key, orb, limit)
    return best


def synastry_hits(
    pos_a: Mapping[str, float],
    pos_b: Mapping[str, float],
    *,
    aspects: Iterable[str],
    policy: Mapping[str, Any],
    per_aspect_weight: Mapping[str, float] | None = None,
    per_pair_weight: Mapping[tuple[str, str], float] | None = None,
) -> list[SynastryHit]:
    """Return matched aspects for all A×B pairs within the configured policy."""

    hits: list[SynastryHit] = []
    for name_a, lon_a in pos_a.items():
        if lon_a is None:
            continue
        for name_b, lon_b in pos_b.items():
            if lon_b is None:
                continue
            delta = angular_sep_deg(float(lon_a), float(lon_b))
            best = _best_aspect(name_a, name_b, delta, aspects, policy)
            if best is None:
                continue
            aspect, orb, limit = best
            w_aspect = 1.0 if per_aspect_weight is None else float(per_aspect_weight.get(aspect, 1.0))
            boost = 1.0 + max(0.0, w_aspect - 1.0) * 4.0
            adj_limit = limit * boost
            base = 0.0 if adj_limit <= 0.0 else max(0.0, 1.0 - orb / adj_limit)
            w_pair = _pair_weight(per_pair_weight, name_a, name_b)
            severity = base * w_aspect * w_pair
            hits.append(
                SynastryHit(
                    a=name_a,
                    b=name_b,
                    aspect=aspect,
                    angle=float(BASE_ASPECTS.get(aspect, 0.0)),
                    delta=float(delta),
                    orb=float(orb),
                    limit=float(limit),
                    severity=severity,
                )
            )
    hits.sort(key=lambda h: (h.a, h.b, h.orb, h.aspect))
    return hits


def synastry_grid(hits: Iterable[SynastryHit]) -> dict[str, dict[str, str]]:
    """Return a simple grid summarising the dominant aspect per pair."""

    best: dict[str, dict[str, SynastryHit]] = {}
    for hit in hits:
        row = best.setdefault(hit.a, {})
        current = row.get(hit.b)
        if current is None or hit.orb < current.orb:
            row[hit.b] = hit
    return {
        a_name: {b_name: entry.aspect for b_name, entry in cols.items()}
        for a_name, cols in best.items()
    }


def overlay_positions(pos_a: Mapping[str, float], pos_b: Mapping[str, float]) -> dict[str, dict[str, float]]:
    """Return overlay of chart positions keyed by body."""

    overlay: dict[str, dict[str, float]] = {}
    for name in sorted(set(pos_a.keys()) | set(pos_b.keys())):
        entry: dict[str, float] = {}
        if name in pos_a and pos_a[name] is not None:
            entry["A"] = float(pos_a[name])
        if name in pos_b and pos_b[name] is not None:
            entry["B"] = float(pos_b[name])
        if "A" in entry and "B" in entry:
            entry["delta"] = angular_sep_deg(entry["A"], entry["B"])
        if "A" in entry:
            entry.setdefault("ring", "A")
        elif "B" in entry:
            entry.setdefault("ring", "B")
        overlay[name] = entry
    return overlay


def synastry_score(hits: Iterable[SynastryHit]) -> dict[str, Any]:
    """Aggregate severity across the hit list."""

    total = 0.0
    per_aspect: dict[str, float] = {}
    per_pair: dict[str, float] = {}
    count = 0
    for hit in hits:
        severity = float(hit.severity)
        total += severity
        per_aspect[hit.aspect] = per_aspect.get(hit.aspect, 0.0) + severity
        key = f"{hit.a}→{hit.b}"
        per_pair[key] = per_pair.get(key, 0.0) + severity
        count += 1
    average = total / count if count else 0.0
    return {
        "total": total,
        "average": average,
        "per_aspect": per_aspect,
        "per_pair": per_pair,
        "count": count,
        "overall": total,
        "by_aspect": per_aspect,
        "by_pair": per_pair,
    }


__all__ = [
    "SynastryHit",
    "synastry_grid",
    "synastry_hits",
    "synastry_score",
    "overlay_positions",
]
