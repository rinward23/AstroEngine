"""Aspect detection for heliocentric transit ↔ natal overlays."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .engine import OverlayBodyState

__all__ = [
    "TRANSIT_ORB_LIMITS",
    "AspectHit",
    "compute_transit_aspects",
]


# Default orb allowances (degrees) keyed by canonical body name.
TRANSIT_ORB_LIMITS: Mapping[str, float] = {
    "sun": 6.0,
    "moon": 5.0,
    "mercury": 4.0,
    "venus": 4.0,
    "mars": 4.0,
    "jupiter": 4.0,
    "saturn": 3.0,
    "uranus": 2.0,
    "neptune": 2.0,
    "pluto": 2.0,
    "mean_node": 2.0,
    "asc": 2.0,
    "mc": 2.0,
    "chiron": 2.0,
}


@dataclass(frozen=True)
class AspectHit:
    """Simple container describing an aspect between natal and transit placements."""

    body: str
    kind: str
    separation_deg: float
    orb_abs_deg: float


def _circular_delta(a: float, b: float) -> float:
    diff = (a - b) % 360.0
    return 360.0 - diff if diff > 180.0 else diff


def compute_transit_aspects(
    natal: Mapping[str, OverlayBodyState],
    transit: Mapping[str, OverlayBodyState],
    *,
    conj_override: float | None = None,
    opp_override: float | None = None,
    per_body_overrides: Mapping[str, float] | None = None,
) -> list[AspectHit]:
    """Return conjunction/opposition hits for matching bodies."""

    overrides = dict(per_body_overrides or {})
    hits: list[AspectHit] = []
    for body, natal_state in natal.items():
        transit_state = transit.get(body)
        if transit_state is None:
            continue
        separation = _circular_delta(natal_state.lon_deg, transit_state.lon_deg)
        orb_limit = overrides.get(body, TRANSIT_ORB_LIMITS.get(body, 2.0))
        if conj_override is not None:
            orb_limit = min(orb_limit, conj_override)
        if separation <= orb_limit:
            hits.append(
                AspectHit(body=body, kind="conjunction", separation_deg=separation, orb_abs_deg=separation)
            )
        opp_delta = abs(180.0 - separation)
        opp_limit = overrides.get(body, TRANSIT_ORB_LIMITS.get(body, 2.0))
        if opp_override is not None:
            opp_limit = min(opp_limit, opp_override)
        if opp_delta <= opp_limit:
            hits.append(
                AspectHit(body=body, kind="opposition", separation_deg=180.0 - opp_delta, orb_abs_deg=opp_delta)
            )
    return hits
