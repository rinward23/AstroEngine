"""Synastry helpers for the relationship API."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence

import numpy as np

from .models import (
    Aspect,
    ChartPositions,
    GridCell,
    Hit,
    OrbPolicy,
    Overlay,
    Scores,
    SynastryRequest,
    SynastryResponse,
    Weights,
)

BODY_FAMILY = {
    "Sun": "luminary",
    "Moon": "luminary",
    "Mercury": "personal",
    "Venus": "personal",
    "Mars": "personal",
    "Jupiter": "social",
    "Saturn": "social",
    "Uranus": "outer",
    "Neptune": "outer",
    "Pluto": "outer",
    "Chiron": "points",
    "Node": "points",
}

ASPECT_FAMILY = {
    0: "neutral",
    30: "neutral",
    45: "challenging",
    60: "harmonious",
    72: "harmonious",
    90: "challenging",
    120: "harmonious",
    135: "challenging",
    144: "harmonious",
    150: "challenging",
    180: "challenging",
}

DEFAULT_ORB_POLICY = OrbPolicy(
    base_orb_by_body={
        "Sun": 8.0,
        "Moon": 8.0,
        "Mercury": 6.0,
        "Venus": 6.0,
        "Mars": 6.0,
        "Jupiter": 5.0,
        "Saturn": 5.0,
        "Uranus": 5.0,
        "Neptune": 5.0,
        "Pluto": 5.0,
        "Chiron": 5.0,
        "Node": 5.0,
        "luminary": 8.0,
        "personal": 6.0,
        "social": 5.0,
        "outer": 5.0,
        "points": 5.0,
    },
    cap_by_aspect={
        0: 8.0,
        30: 2.0,
        45: 2.0,
        60: 4.0,
        72: 1.5,
        90: 6.0,
        120: 6.0,
        135: 2.0,
        144: 1.5,
        150: 2.0,
        180: 8.0,
    },
)

DEFAULT_WEIGHTS = Weights(
    aspect_family={"harmonious": 1.0, "challenging": 1.0, "neutral": 0.8},
    body_family={
        "luminary": 1.2,
        "personal": 1.0,
        "social": 0.8,
        "outer": 0.8,
        "points": 0.9,
    },
    conjunction_sign=1.0,
)

DEFAULT_ASPECTS: tuple[Aspect, ...] = (0, 30, 45, 60, 72, 90, 120, 135, 144, 150, 180)


def chart_longitudes(chart: ChartPositions) -> dict[str, float]:
    return {key: float(pos.lon) for key, pos in chart.root.items()}


def _resolve_base_orb(body: str, policy: OrbPolicy) -> float:
    mapping = policy.base_orb_by_body or {}
    if body in mapping:
        return float(mapping[body])
    family = BODY_FAMILY.get(body)
    if family and family in mapping:
        return float(mapping[family])
    return float(DEFAULT_ORB_POLICY.base_orb_by_body.get(body, 5.0))


def _aspect_cap(angle: int, policy: OrbPolicy) -> float:
    caps = policy.cap_by_aspect or {}
    if angle in caps:
        return float(caps[angle])
    return float(DEFAULT_ORB_POLICY.cap_by_aspect.get(angle, 3.0))


def _pair_base_orb(body_a: str, body_b: str, policy: OrbPolicy) -> float:
    a = _resolve_base_orb(body_a, policy)
    b = _resolve_base_orb(body_b, policy)
    return max(0.1, (a + b) / 2.0)


def _pair_body_weight(body_a: str, body_b: str, weights: Weights) -> float:
    mapping = weights.body_family or {}
    default = DEFAULT_WEIGHTS.body_family
    fam_a = BODY_FAMILY.get(body_a)
    fam_b = BODY_FAMILY.get(body_b)
    w_a = float(mapping.get(fam_a, default.get(fam_a, 1.0))) if fam_a else 1.0
    w_b = float(mapping.get(fam_b, default.get(fam_b, 1.0))) if fam_b else 1.0
    return max(0.1, (w_a + w_b) / 2.0)


def _aspect_weight(angle: int, weights: Weights) -> float:
    family = ASPECT_FAMILY.get(angle, "neutral")
    mapping = weights.aspect_family or {}
    default = DEFAULT_WEIGHTS.aspect_family
    return float(mapping.get(family, default.get(family, 1.0)))


def _same_sign(lon_a: float, lon_b: float) -> bool:
    return int(lon_a // 30.0) == int(lon_b // 30.0)


def _angular_sep(lon_a: float, lon_b: float) -> float:
    return abs(((lon_a - lon_b + 180.0) % 360.0) - 180.0)


def _compute_hits(
    pos_a: dict[str, float],
    pos_b: dict[str, float],
    *,
    aspects: Sequence[Aspect],
    policy: OrbPolicy,
    weights: Weights,
    gamma: float,
) -> list[Hit]:
    bodies_a = sorted(pos_a.keys())
    bodies_b = sorted(pos_b.keys())
    if not bodies_a or not bodies_b:
        return []
    arr_a = np.array([pos_a[name] for name in bodies_a], dtype=float)
    arr_b = np.array([pos_b[name] for name in bodies_b], dtype=float)
    sep = np.abs(((arr_a[:, None] - arr_b[None, :]) + 180.0) % 360.0 - 180.0)
    base_matrix = np.array(
        [[_pair_base_orb(a, b, policy) for b in bodies_b] for a in bodies_a],
        dtype=float,
    )
    body_weight_matrix = np.array(
        [[_pair_body_weight(a, b, weights) for b in bodies_b] for a in bodies_a],
        dtype=float,
    )
    same_sign_matrix = np.equal(np.floor(arr_a[:, None] / 30.0), np.floor(arr_b[None, :] / 30.0))

    hits: list[Hit] = []
    for aspect in aspects:
        cap = _aspect_cap(int(aspect), policy)
        limit_matrix = np.minimum(base_matrix, cap)
        orb_matrix = np.abs(sep - float(aspect))
        mask = orb_matrix <= limit_matrix
        indices = np.argwhere(mask)
        if indices.size == 0:
            continue
        aspect_weight = _aspect_weight(int(aspect), weights)
        for idx in indices:
            i, j = int(idx[0]), int(idx[1])
            limit = float(limit_matrix[i, j])
            if limit <= 0:
                continue
            orb = float(orb_matrix[i, j])
            base_severity = max(0.0, 1.0 - orb / limit)
            severity = base_severity * aspect_weight * float(body_weight_matrix[i, j])
            if aspect == 0 and same_sign_matrix[i, j]:
                severity *= float(weights.conjunction_sign)
            severity = min(1.0, max(0.0, severity))
            if gamma != 1.0:
                severity = pow(severity, gamma)
            hits.append(
                Hit(
                    bodyA=bodies_a[i],
                    bodyB=bodies_b[j],
                    aspect=int(aspect),
                    delta=float(sep[i, j]),
                    orb=orb,
                    severity=severity,
                )
            )
    hits.sort(key=lambda h: (-h.severity, h.orb, h.bodyA, h.bodyB, h.aspect))
    return hits


def _grid_from_hits(hits: Iterable[Hit]) -> dict[str, dict[str, GridCell]]:
    grid: dict[str, dict[str, GridCell]] = {}
    for hit in hits:
        rows = grid.setdefault(hit.bodyA, {})
        cell = rows.get(hit.bodyB)
        if cell is None or (cell.best and hit.severity > cell.best.severity):
            rows[hit.bodyB] = GridCell(best=hit)
    return grid


def _overlay(pos_a: dict[str, float], pos_b: dict[str, float], hits: Iterable[Hit]) -> Overlay:
    wheel_a = sorted(((name, float(lon)) for name, lon in pos_a.items()), key=lambda item: item[0])
    wheel_b = sorted(((name, float(lon)) for name, lon in pos_b.items()), key=lambda item: item[0])
    index_a = {name: lon for name, lon in wheel_a}
    index_b = {name: lon for name, lon in wheel_b}
    lines = []
    for hit in hits:
        lon_a = index_a.get(hit.bodyA)
        lon_b = index_b.get(hit.bodyB)
        if lon_a is None or lon_b is None:
            continue
        lines.append(
            {
                "from": {"body": hit.bodyA, "lon": lon_a},
                "to": {"body": hit.bodyB, "lon": lon_b},
                "aspect": hit.aspect,
                "severity": hit.severity,
            }
        )
    return Overlay(wheelA=list(wheel_a), wheelB=list(wheel_b), lines=lines)


def _scores(hits: Iterable[Hit]) -> Scores:
    per_aspect: dict[str, float] = defaultdict(float)
    per_body: dict[str, float] = defaultdict(float)
    total = 0.0
    for hit in hits:
        total += hit.severity
        family = ASPECT_FAMILY.get(hit.aspect, "neutral")
        per_aspect[family] += hit.severity
        fam_a = BODY_FAMILY.get(hit.bodyA)
        fam_b = BODY_FAMILY.get(hit.bodyB)
        if fam_a:
            per_body[fam_a] += hit.severity / 2.0
        if fam_b:
            per_body[fam_b] += hit.severity / 2.0
    return Scores(
        by_aspect_family=dict(sorted(per_aspect.items())),
        by_body_family=dict(sorted(per_body.items())),
        overall=total,
    )


def resolve_aspects(request: SynastryRequest) -> tuple[Aspect, ...]:
    return request.aspects or DEFAULT_ASPECTS


def resolve_policy(request: SynastryRequest) -> OrbPolicy:
    if request.orb_policy is not None:
        return request.orb_policy
    return DEFAULT_ORB_POLICY


def resolve_weights(request: SynastryRequest) -> Weights:
    if request.weights is not None:
        return request.weights
    return DEFAULT_WEIGHTS


def compute_synastry(request: SynastryRequest) -> SynastryResponse:
    aspects = resolve_aspects(request)
    policy = resolve_policy(request)
    weights = resolve_weights(request)
    pos_a = chart_longitudes(request.positionsA)
    pos_b = chart_longitudes(request.positionsB)
    hits = _compute_hits(pos_a, pos_b, aspects=aspects, policy=policy, weights=weights, gamma=float(request.gamma))
    if request.min_severity > 0:
        hits = [hit for hit in hits if hit.severity >= request.min_severity]
    if request.top_k is not None:
        hits = hits[: request.top_k]
    if request.limit is not None:
        start = request.offset
        end = start + request.limit
        hits_page = hits[start:end]
    else:
        hits_page = hits[request.offset :]
    grid = _grid_from_hits(hits_page)
    overlay = _overlay(pos_a, pos_b, hits_page)
    scores = _scores(hits_page)
    return SynastryResponse(hits=hits_page, grid=grid, overlay=overlay, scores=scores)


__all__ = [
    "compute_synastry",
    "chart_longitudes",
    "DEFAULT_ORB_POLICY",
    "DEFAULT_WEIGHTS",
]
