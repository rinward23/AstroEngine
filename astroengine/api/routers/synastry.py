"""FastAPI router exposing synastry operations."""

from __future__ import annotations

from collections import Counter

from fastapi import APIRouter

from ...chart.natal import DEFAULT_BODIES
from ...synastry.orchestrator import compute_synastry
from ..schemas_synastry import SynastryHit, SynastryRequest, SynastryResponse

router = APIRouter()


@router.post("/aspects", response_model=SynastryResponse)
def synastry_aspects(req: SynastryRequest) -> SynastryResponse:
    """Compute directional synastry aspects for the provided natal charts."""

    hits = compute_synastry(
        a=req.a.model_dump(),
        b=req.b.model_dump(),
        aspects=tuple(req.aspects),
        orb_deg=req.orb_deg,
        bodies_a=tuple(req.bodies_a or DEFAULT_BODIES.keys()),
        bodies_b=tuple(req.bodies_b or DEFAULT_BODIES.keys()),
    )

    items = [
        SynastryHit(
            direction=h.direction,
            moving=h.moving,
            target=h.target,
            aspect=int(h.angle_deg),
            orb=float(h.orb_abs),
            score=h.score,
            domains=h.domains,
        )
        for h in hits
    ]
    summary = Counter(f"{hit.direction}:{hit.aspect}" for hit in items)
    return SynastryResponse(
        count=len(items),
        summary={str(key): value for key, value in summary.items()},
        hits=items,
    )
