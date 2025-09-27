from __future__ import annotations
from datetime import timezone
from importlib import util
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from app.schemas.rel import (
    SynastryRequest,
    SynastryResponse,
    SynastryHit,
    SynastryGrid,
    CompositeMidpointRequest,
    CompositeDavisonRequest,
    CompositeResponse,
)
from core.rel_plus.synastry import synastry_interaspects, synastry_grid
from core.rel_plus.composite import composite_midpoint_positions, davison_positions

if util.find_spec("app.repo.orb_policies") and util.find_spec("app.db.session"):
    from app.repo.orb_policies import OrbPolicyRepo  # type: ignore
    from app.db.session import session_scope  # type: ignore
else:  # pragma: no cover - optional dependency path
    OrbPolicyRepo = None  # type: ignore
    session_scope = None  # type: ignore

from app.routers import aspects as aspects_module

router = APIRouter(prefix="", tags=["Plus"])

DEFAULT_POLICY: Dict[str, Any] = {
    "per_object": {},
    "per_aspect": {
        "conjunction": 8.0,
        "opposition": 7.0,
        "square": 6.0,
        "trine": 6.0,
        "sextile": 4.0,
        "quincunx": 3.0,
        "semisquare": 2.0,
        "sesquisquare": 2.0,
        "quintile": 2.0,
        "biquintile": 2.0,
    },
    "adaptive_rules": {
        "luminaries_factor": 0.9,
        "outers_factor": 1.1,
        "minor_aspect_factor": 0.9,
    },
}


def _resolve_orb_policy(req: SynastryRequest) -> Dict[str, Any]:
    if req.orb_policy_inline is not None:
        return req.orb_policy_inline.model_dump()
    if req.orb_policy_id is not None:
        if OrbPolicyRepo is None or session_scope is None:
            raise HTTPException(
                status_code=400,
                detail="orb_policy_id requires DB; provide orb_policy_inline instead",
            )
        with session_scope() as db:
            rec = OrbPolicyRepo().get(db, req.orb_policy_id)
            if not rec:
                raise HTTPException(status_code=404, detail="orb policy not found")
            return {
                "per_object": rec.per_object or {},
                "per_aspect": rec.per_aspect or {},
                "adaptive_rules": rec.adaptive_rules or {},
            }
    return DEFAULT_POLICY


@router.post(
    "/synastry/compute",
    response_model=SynastryResponse,
    summary="Compute inter‑aspects between Chart A and B",
    description=(
        "Returns best aspect per A×B pair with orb & limits, plus a pair grid of counts."
    ),
)
def synastry_compute(req: SynastryRequest):
    policy = _resolve_orb_policy(req)
    hits_list = synastry_interaspects(req.pos_a, req.pos_b, req.aspects, policy)
    hits = [SynastryHit(**h) for h in hits_list]
    grid = SynastryGrid(counts=synastry_grid(hits_list))
    return SynastryResponse(hits=hits, grid=grid)


@router.post(
    "/composites/midpoint",
    response_model=CompositeResponse,
    summary="Midpoint Composite positions",
    description="Circular midpoints of longitudes for the requested objects.",
)
def composites_midpoint(req: CompositeMidpointRequest):
    pos = composite_midpoint_positions(req.pos_a, req.pos_b, req.objects)
    return CompositeResponse(positions=pos, meta={"method": "midpoint"})


@router.post(
    "/composites/davison",
    response_model=CompositeResponse,
    summary="Davison Composite positions (time midpoint)",
    description=(
        "Computes body longitudes at the UTC time midpoint between two datetimes using the configured ephemeris provider."
    ),
)
def composites_davison(req: CompositeDavisonRequest):
    provider = aspects_module._get_provider()
    pos = davison_positions(req.objects, req.dt_a, req.dt_b, provider)
    mid_a = req.dt_a.astimezone(timezone.utc)
    mid_b = req.dt_b.astimezone(timezone.utc)
    midpoint = mid_a + (mid_b - mid_a) / 2
    return CompositeResponse(
        positions=pos,
        meta={"method": "davison", "midpoint_time": midpoint.isoformat()},
    )
