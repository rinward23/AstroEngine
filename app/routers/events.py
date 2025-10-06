from __future__ import annotations

from datetime import UTC
from typing import Any

from fastapi import APIRouter, HTTPException

from app.routers import aspects as aspects_module
from app.schemas.aspects import TimeWindow
from app.schemas.events import (
    CombustCazimiRequest,
    EventIntervalOut,
    ReturnsRequest,
    VoCMoonRequest,
)
from core.events_plus.detectors import (
    CombustCfg,
    detect_combust_cazimi,
    detect_returns,
    detect_voc_moon,
)

try:  # Optional DB repo for orb policy id
    from app.db.session import session_scope  # type: ignore
    from app.repo.orb_policies import OrbPolicyRepo  # type: ignore
except Exception:  # pragma: no cover
    session_scope = None  # type: ignore
    OrbPolicyRepo = None  # type: ignore

router = APIRouter(prefix="", tags=["Plus"])

DEFAULT_POLICY: dict[str, Any] = {
    "per_object": {},
    "per_aspect": {
        "conjunction": 8.0,
        "opposition": 7.0,
        "square": 6.0,
        "trine": 6.0,
        "sextile": 3.0,
        "quincunx": 3.0,
    },
    "adaptive_rules": {},
}


def _resolve_policy_inline_or_id(inline, pid) -> dict[str, Any]:
    if inline is not None:
        return inline.model_dump()
    if pid is not None:
        if OrbPolicyRepo is None or session_scope is None:
            raise HTTPException(
                status_code=400,
                detail="orb_policy_id requires DB; provide orb_policy_inline instead",
            )
        with session_scope() as db:
            rec = OrbPolicyRepo().get(db, pid)
            if not rec:
                raise HTTPException(status_code=404, detail="orb policy not found")
            return {
                "per_object": rec.per_object or {},
                "per_aspect": rec.per_aspect or {},
                "adaptive_rules": rec.adaptive_rules or {},
            }
    return DEFAULT_POLICY


@router.post(
    "/events/voc-moon",
    response_model=list[EventIntervalOut],
    summary="Void-of-Course Moon intervals",
    description=(
        "Returns intervals where the Moon makes no selected aspects to chosen bodies before sign ingress."
    ),
)
def voc_moon(req: VoCMoonRequest):
    provider = aspects_module._get_provider()
    policy = _resolve_policy_inline_or_id(req.orb_policy_inline, req.orb_policy_id)
    win = TimeWindow(
        start=req.window.start.astimezone(UTC),
        end=req.window.end.astimezone(UTC),
    )
    intervals = detect_voc_moon(
        win,
        provider,
        req.aspects,
        policy,
        req.other_objects,
        step_minutes=req.step_minutes,
    )
    return [
        EventIntervalOut(kind=i.kind, start=i.start, end=i.end, meta=i.meta) for i in intervals
    ]


@router.post(
    "/events/combust-cazimi",
    response_model=list[EventIntervalOut],
    summary="Combust / Cazimi / Under-beams intervals",
    description=(
        "Returns disjoint intervals for cazimi (⊂ combust) and under-beams based on Sun–planet separation thresholds."
    ),
)
def combust_cazimi(req: CombustCazimiRequest):
    provider = aspects_module._get_provider()
    cfg = CombustCfg(
        cazimi_deg=req.cfg.cazimi_deg,
        combust_deg=req.cfg.combust_deg,
        under_beams_deg=req.cfg.under_beams_deg,
    )
    win = TimeWindow(
        start=req.window.start.astimezone(UTC),
        end=req.window.end.astimezone(UTC),
    )
    intervals = detect_combust_cazimi(
        win,
        provider,
        planet=req.planet,
        cfg=cfg,
        step_minutes=req.step_minutes,
    )
    return [
        EventIntervalOut(kind=i.kind, start=i.start, end=i.end, meta=i.meta) for i in intervals
    ]


@router.post(
    "/events/returns",
    response_model=list[EventIntervalOut],
    summary="Return events (points)",
    description="Emits point events when a body returns to its natal longitude within the given window.",
)
def returns(req: ReturnsRequest):
    provider = aspects_module._get_provider()
    win = TimeWindow(
        start=req.window.start.astimezone(UTC),
        end=req.window.end.astimezone(UTC),
    )
    intervals = detect_returns(
        win,
        provider,
        body=req.body,
        target_lon=req.target_lon,
        step_minutes=req.step_minutes,
    )
    return [
        EventIntervalOut(kind=i.kind, start=i.start, end=i.end, meta=i.meta) for i in intervals
    ]
