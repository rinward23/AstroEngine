"""Synastry orchestration helpers."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from ..chart.natal import DEFAULT_BODIES, ChartLocation, compute_natal_chart
from ..core.domains import DEFAULT_PLANET_DOMAIN_WEIGHTS
from ..utils.angles import delta_angle

__all__ = ["SynHit", "compute_synastry"]


@dataclass(frozen=True)
class SynHit:
    """Represents a directional synastry aspect hit."""

    direction: str  # "A->B" | "B->A"
    moving: str
    target: str
    angle_deg: float
    orb_abs: float
    score: float | None = None
    domains: dict[str, float] | None = None


def _parse_timestamp(iso_ts: Any) -> datetime:
    if not isinstance(iso_ts, str):
        raise TypeError("timestamp must be ISO-8601 string")
    dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    else:
        dt = dt.astimezone(UTC)
    return dt


def _normalize_body_names(candidates: Iterable[str] | None, available: set[str]) -> list[str]:
    fallback = [name for name in DEFAULT_BODIES if name in available]
    if not candidates:
        return fallback or sorted(available)
    normalized: list[str] = []
    for name in candidates:
        key = str(name).strip()
        if not key:
            continue
        if key in available:
            normalized.append(key)
    if not normalized:
        return fallback or sorted(available)
    return normalized


def _domain_hint(moving: str, target: str) -> dict[str, float] | None:
    weights: dict[str, float] = {}
    for body in (moving, target):
        key = body.lower().replace(" ", "_")
        planet_weights = DEFAULT_PLANET_DOMAIN_WEIGHTS.get(key)
        if not planet_weights:
            continue
        for domain, value in planet_weights.items():
            weights[domain] = weights.get(domain, 0.0) + float(value)
    if not weights:
        return None
    total = sum(weights.values())
    if total <= 0:
        return None
    return {domain: value / total for domain, value in weights.items()}


def _score_for_hit(orb_abs: float, orb_allow: float) -> float | None:
    if orb_allow <= 0:
        return 1.0 if orb_abs == 0 else None
    ratio = max(0.0, 1.0 - (orb_abs / orb_allow))
    return ratio


def _compute_directional_hits(
    *,
    direction: str,
    moving_bodies: Sequence[str],
    target_bodies: Sequence[str],
    moving_longitudes: dict[str, float],
    target_longitudes: dict[str, float],
    aspects: Sequence[int],
    orb_deg: float,
) -> list[SynHit]:
    hits: list[SynHit] = []
    for moving in moving_bodies:
        lon_m = moving_longitudes.get(moving)
        if lon_m is None:
            continue
        for target in target_bodies:
            if moving == target:
                continue
            lon_t = target_longitudes.get(target)
            if lon_t is None:
                continue
            separation = abs(delta_angle(lon_m, lon_t))
            for angle in aspects:
                angle_val = float(angle)
                orb_abs = abs(separation - angle_val)
                if orb_abs <= orb_deg:
                    score = _score_for_hit(orb_abs, orb_deg)
                    domains = _domain_hint(moving, target)
                    hits.append(
                        SynHit(
                            direction=direction,
                            moving=moving,
                            target=target,
                            angle_deg=angle_val,
                            orb_abs=orb_abs,
                            score=score,
                            domains=domains,
                        )
                    )
    return hits


def compute_synastry(
    *,
    a: dict,
    b: dict,
    aspects: Sequence[int],
    orb_deg: float,
    bodies_a: Sequence[str] | None = None,
    bodies_b: Sequence[str] | None = None,
) -> list[SynHit]:
    """Return merged A→B/B→A aspect hits for the provided natal charts."""

    moment_a = _parse_timestamp(a["ts"])
    moment_b = _parse_timestamp(b["ts"])
    location_a = ChartLocation(latitude=float(a["lat"]), longitude=float(a["lon"]))
    location_b = ChartLocation(latitude=float(b["lat"]), longitude=float(b["lon"]))

    chart_a = compute_natal_chart(moment_a, location_a)
    chart_b = compute_natal_chart(moment_b, location_b)

    longitudes_a = {name: pos.longitude for name, pos in chart_a.positions.items()}
    longitudes_b = {name: pos.longitude for name, pos in chart_b.positions.items()}

    available_a = set(longitudes_a)
    available_b = set(longitudes_b)

    bodies_a_resolved = _normalize_body_names(bodies_a, available_a)
    bodies_b_resolved = _normalize_body_names(bodies_b, available_b)

    dir_ab = _compute_directional_hits(
        direction="A->B",
        moving_bodies=bodies_a_resolved,
        target_bodies=bodies_b_resolved,
        moving_longitudes=longitudes_a,
        target_longitudes=longitudes_b,
        aspects=aspects,
        orb_deg=orb_deg,
    )
    dir_ba = _compute_directional_hits(
        direction="B->A",
        moving_bodies=bodies_b_resolved,
        target_bodies=bodies_a_resolved,
        moving_longitudes=longitudes_b,
        target_longitudes=longitudes_a,
        aspects=aspects,
        orb_deg=orb_deg,
    )

    hits = dir_ab + dir_ba
    hits.sort(key=lambda h: (h.direction, h.moving, h.target, h.angle_deg, h.orb_abs))
    return hits
