from __future__ import annotations
from typing import Any, Dict
from datetime import timezone

from fastapi import APIRouter, HTTPException

from app.schemas.electional import (
    ElectionalSearchRequest,
    ElectionalSearchResponse,
    WindowOut,
    InstantOut,
    InstantMatch,
    InstantViolation,
)
from app.schemas.aspects import TimeWindow

from core.electional_plus.engine import (
    ElectionalRules,
    AspectRule,
    ForbiddenRule,
    search_best_windows,
)

# Optional DB orb policy
try:
    from app.repo.orb_policies import OrbPolicyRepo  # type: ignore
    from app.db.session import session_scope  # type: ignore
except Exception:  # pragma: no cover
    OrbPolicyRepo = None  # type: ignore
    session_scope = None  # type: ignore

# Provider injection reused from aspects
from app.routers import aspects as aspects_module

router = APIRouter(prefix="", tags=["Plus"])  # group under Plus

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


def _resolve_policy(inline, pid) -> Dict[str, Any]:
    if inline is not None:
        return inline.model_dump()
    if pid is not None:
        if OrbPolicyRepo is None or session_scope is None:
            raise HTTPException(status_code=400, detail="orb_policy_id requires DB; provide orb_policy_inline instead")
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
    "/electional/search",
    response_model=ElectionalSearchResponse,
    summary="Search best electional windows",
    description="Sliding‑window optimizer that ranks time windows by rules (required/forbidden aspects, VoC avoidance, time filters).",
)
def electional_search(req: ElectionalSearchRequest):
    provider = aspects_module._get_provider()
    policy = _resolve_policy(req.orb_policy_inline, req.orb_policy_id)

    rules = ElectionalRules(
        window=TimeWindow(start=req.window.start.astimezone(timezone.utc), end=req.window.end.astimezone(timezone.utc)),
        window_minutes=req.window_minutes,
        step_minutes=req.step_minutes,
        top_k=req.top_k,
        avoid_voc_moon=req.avoid_voc_moon,
        allowed_weekdays=req.allowed_weekdays,
        allowed_utc_ranges=req.allowed_utc_ranges,
        orb_policy=policy,
        required_aspects=[AspectRule(**r.model_dump()) for r in req.required_aspects],
        forbidden_aspects=[ForbiddenRule(**r.model_dump()) for r in req.forbidden_aspects],
    )

    results = search_best_windows(rules, provider)

    def _map_instant(I) -> InstantOut:
        if isinstance(I, dict):
            data = I
        else:
            data = {
                "ts": getattr(I, "ts"),
                "score": getattr(I, "score", 0.0),
                "reason": getattr(I, "reason", None),
                "matches": getattr(I, "matches", []),
                "violations": getattr(I, "violations", []),
            }
        return InstantOut(
            ts=data.get("ts"),
            score=data.get("score", 0.0),
            reason=data.get("reason"),
            matches=[InstantMatch(**m) for m in data.get("matches", [])],
            violations=[InstantViolation(**v) for v in data.get("violations", [])],
        )

    windows = [
        WindowOut(
            start=R.start,
            end=R.end,
            score=R.score,
            samples=R.samples,
            avg_score=R.avg_score,
            top_instants=[_map_instant(i) for i in R.top_instants],
            breakdown=R.breakdown,
        )
        for R in results
    ]

    return ElectionalSearchResponse(windows=windows, meta={"count": len(windows)})
