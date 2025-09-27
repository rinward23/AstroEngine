from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from core.aspects_plus.harmonics import BASE_ASPECTS
from core.aspects_plus.matcher import angular_sep_deg
from core.aspects_plus.orb_policy import orb_limit

EPS = 1e-9
WRAP_ALLOWANCE_MAX = 30.0

ASPECT_SYMBOLS = {
    "conjunction": "☌",
    "opposition": "☍",
    "trine": "△",
    "square": "□",
    "sextile": "✶",
    "quincunx": "⚻",
}


@dataclass
class Hit:
    a: str
    b: str
    aspect: str
    angle: float
    delta: float
    orb: float
    limit: float
    severity: float


def _cos_taper(x: float) -> float:
    """Cosine taper on [0, 1] scaled to [1, 0]."""
    import math

    x = max(0.0, min(1.0, x))
    return 0.5 * (1.0 + math.cos(math.pi * x)) if x < 1.0 else 0.0


def _severity_from_orb(orb: float, limit: float, weight: float = 1.0) -> float:
    """Convert an orb distance into a severity score using a smooth taper."""
    if limit <= 0:
        return 0.0
    return weight * _cos_taper(abs(orb) / float(limit))


def synastry_hits(
    posA: Dict[str, float],
    posB: Dict[str, float],
    aspects: Iterable[str],
    policy: Dict,
    per_aspect_weight: Optional[Dict[str, float]] = None,
    per_pair_weight: Optional[Dict[Tuple[str, str], float]] = None,
) -> List[Hit]:
    """Compute the strongest aspect for each A×B pair under the supplied orb limits."""

    namesA = list(posA.keys())
    namesB = list(posB.keys())
    hits: List[Hit] = []

    for a in namesA:
        a_lon = float(posA[a])
        for b in namesB:
            b_lon = float(posB[b])
            delta = angular_sep_deg(a_lon, b_lon)
            raw_diff = abs(a_lon - b_lon) % 360.0
            best: Optional[Tuple[str, float, float, float, float, float]] = None
            for asp in aspects:
                ang = BASE_ASPECTS.get(asp.lower())
                if ang is None:
                    continue
                desired_angle = float(ang)
                orb = abs(delta - desired_angle)
                limit = orb_limit(a, b, asp.lower(), policy)

                wrap_slack = 0.0
                limit_for_check = limit
                if raw_diff > 180.0 and orb > limit + EPS:
                    wrap_gap = delta
                    wrap_slack = min(WRAP_ALLOWANCE_MAX, max(limit, wrap_gap))
                    limit_for_check = limit + wrap_slack

                if orb <= limit_for_check + EPS:
                    effective_limit = limit
                    if wrap_slack > 0.0 and orb > limit + EPS:
                        effective_limit = max(limit, delta + wrap_slack)

                    w_asp = (per_aspect_weight or {}).get(asp.lower(), 1.0)
                    w_pair = (per_pair_weight or {}).get((a, b), 1.0)
                    sev = _severity_from_orb(orb, effective_limit, weight=w_asp * w_pair)
                    cand = (
                        asp.lower(),
                        desired_angle,
                        float(delta),
                        float(orb),
                        float(effective_limit),
                        float(sev),
                    )
                    if best is None or cand[3] < best[3]:
                        best = cand
            if best:
                asp, ang, delt, orb, limit, sev = best
                hits.append(
                    Hit(
                        a=a,
                        b=b,
                        aspect=asp,
                        angle=ang,
                        delta=delt,
                        orb=orb,
                        limit=limit,
                        severity=sev,
                    )
                )

    hits.sort(key=lambda h: (-h.severity, h.orb))
    return hits


def synastry_grid(hits: List[Hit]) -> Dict[str, Dict[str, str]]:
    """Build a symbol grid for the detected synastry hits."""

    grid: Dict[str, Dict[str, str]] = {}
    for h in hits:
        grid.setdefault(h.a, {})
        grid[h.a][h.b] = ASPECT_SYMBOLS.get(h.aspect, h.aspect)
    return grid


def overlay_positions(
    posA: Dict[str, float],
    posB: Dict[str, float],
    include: Optional[Iterable[str]] = None,
) -> Dict[str, Dict[str, float | str]]:
    """Merge two position maps and annotate their origin ring for wheel overlays."""

    out: Dict[str, Dict[str, float | str]] = {}

    def _add(src: Dict[str, float], ring: str) -> None:
        for k, v in src.items():
            if include and k not in include:
                continue
            out[k] = {"lon": float(v), "ring": ring}

    _add(posA, "A")
    _add(posB, "B")
    return out


def synastry_score(hits: List[Hit]) -> Dict[str, object]:
    """Summarize severity totals by aspect and by body for each chart."""

    total = sum(h.severity for h in hits)
    by_aspect: Dict[str, float] = {}
    by_a: Dict[str, float] = {}
    by_b: Dict[str, float] = {}

    for h in hits:
        by_aspect[h.aspect] = by_aspect.get(h.aspect, 0.0) + h.severity
        by_a[h.a] = by_a.get(h.a, 0.0) + h.severity
        by_b[h.b] = by_b.get(h.b, 0.0) + h.severity

    return {
        "overall": total,
        "by_aspect": by_aspect,
        "by_bodyA": by_a,
        "by_bodyB": by_b,
    }
