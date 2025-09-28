from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query

from app.schemas.relationship import (
    SynastryRequest,
    SynastryResponse,
    SynastryHitOut,
    CompositeRequest,
    CompositeResponse,
    DavisonRequest,
    DavisonResponse,
)
from app.schemas.aspects import OrbPolicyInline

from core.relationship_plus.synastry import (
    synastry_hits,
    synastry_grid,
    overlay_positions,
    synastry_score,
)
from core.relationship_plus.composite import (
    composite_positions,
    davison_positions,
    davison_midpoints,
    Geo,
)
from core.rel_plus import (
    BirthEvent,
    DavisonResult,
    composite_houses,
    davison_houses,
)

from app.routers import aspects as aspects_module

router = APIRouter(prefix="/relationship", tags=["Relationship"])

DEFAULT_POLICY: Dict[str, Any] = {
    "per_object": {},
    "per_aspect": {
        "conjunction": 8.0,
        "opposition": 7.0,
        "square": 6.0,
        "trine": 6.0,
        "sextile": 3.0,
    },
    "adaptive_rules": {},
}


def _resolve_policy(inline: OrbPolicyInline | None) -> Dict[str, Any]:
    return inline.model_dump() if inline is not None else DEFAULT_POLICY


@router.post("/synastry", response_model=SynastryResponse, summary="Synastry inter-aspect analysis")
def api_synastry(req: SynastryRequest):
    policy = _resolve_policy(req.orb_policy_inline)
    hits = synastry_hits(
        req.posA,
        req.posB,
        aspects=req.aspects,
        policy=policy,
        per_aspect_weight=req.per_aspect_weight,
        per_pair_weight=req.per_pair_weight,
    )
    grid = synastry_grid(hits)
    overlay = overlay_positions(req.posA, req.posB)
    scores = synastry_score(hits)
    return SynastryResponse(
        hits=[SynastryHitOut(**h.__dict__) for h in hits],
        grid=grid,
        overlay=overlay,
        scores=scores,
        meta={"count": len(hits)},
    )


@router.post("/composite", response_model=CompositeResponse, summary="Composite (midpoint) positions")
def api_composite(
    req: CompositeRequest,
    houses: bool = Query(False, description="Include composite houses in response"),
    hsys: str = Query("P", description="Requested house system code"),
):
    pos = composite_positions(req.posA, req.posB, bodies=req.bodies)
    houses_payload = None
    if houses:
        if req.eventA is None or req.eventB is None:
            raise HTTPException(status_code=400, detail="eventA and eventB are required when houses=true")
        event_a = BirthEvent(when=req.eventA.when, lat=req.eventA.lat_deg, lon=req.eventA.lon_deg_east)
        event_b = BirthEvent(when=req.eventB.when, lat=req.eventB.lat_deg, lon=req.eventB.lon_deg_east)
        houses_payload = composite_houses(event_a, event_b, hsys).to_payload()
    return CompositeResponse(positions=pos, meta={"bodies": list(pos.keys())}, houses=houses_payload)


@router.post("/davison", response_model=DavisonResponse, summary="Davison chart at time midpoint (MVP)")
def api_davison(
    req: DavisonRequest,
    houses: bool = Query(False, description="Include Davison houses in response"),
    hsys: str = Query("P", description="Requested house system code"),
):
    provider = aspects_module._get_provider()
    geo_a = Geo(lat_deg=req.locA.lat_deg, lon_deg_east=req.locA.lon_deg_east)
    geo_b = Geo(lat_deg=req.locB.lat_deg, lon_deg_east=req.locB.lon_deg_east)
    pos = davison_positions(provider, req.dtA, geo_a, req.dtB, geo_b, bodies=req.bodies)
    mid_dt, mid_lat, mid_lon = davison_midpoints(req.dtA, geo_a, req.dtB, geo_b)
    houses_payload = None
    if houses:
        davison_result = DavisonResult(mid_when=mid_dt, mid_lat=mid_lat, mid_lon=mid_lon, positions={})
        houses_payload = davison_houses(davison_result, hsys).to_payload()
    return DavisonResponse(
        positions=pos,
        midpoint_time_utc=mid_dt,
        midpoint_geo=req.locA.__class__(lat_deg=mid_lat, lon_deg_east=mid_lon),
        meta={"bodies": list(pos.keys())},
        houses=houses_payload,
    )
