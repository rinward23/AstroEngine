from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from app.schemas.series import (
    DailyPoint,
    MonthlyPoint,
    ScoreSeriesRequest,
    ScoreSeriesResponse,
)
from astroengine.core.aspects_plus.aggregate import rank_hits
from astroengine.core.aspects_plus.scan import TimeWindow, scan_time_range
from astroengine.core.scan_plus.ranking import (
    EventPoint,
    daily_composite,
    monthly_composite,
    severity as compute_severity,
)

try:  # Optional: DB repo for orb policy id
    from app.repo.orb_policies import OrbPolicyRepo  # type: ignore
    from app.db.session import session_scope  # type: ignore
except Exception:  # pragma: no cover
    OrbPolicyRepo = None  # type: ignore
    session_scope = None  # type: ignore

from app.schemas.aspects import OrbPolicyInline

# Reuse provider injection from aspects router
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


def _resolve_orb_policy_inline_or_id(
    orb_policy_inline: OrbPolicyInline | None,
    orb_policy_id: int | None,
) -> Dict[str, Any]:
    if orb_policy_inline is not None:
        return orb_policy_inline.model_dump()
    if orb_policy_id is not None:
        if OrbPolicyRepo is None or session_scope is None:
            raise HTTPException(
                status_code=400,
                detail="orb_policy_id requires DB repos; provide orb_policy_inline instead",
            )
        with session_scope() as db:
            rec = OrbPolicyRepo().get(db, orb_policy_id)
            if not rec:
                raise HTTPException(status_code=404, detail="orb policy not found")
            return {
                "per_object": rec.per_object or {},
                "per_aspect": rec.per_aspect or {},
                "adaptive_rules": rec.adaptive_rules or {},
            }
    return DEFAULT_POLICY


@router.post(
    "/transits/score-series",
    response_model=ScoreSeriesResponse,
    summary="Daily & monthly composite severity",
)
def score_series(req: ScoreSeriesRequest):
    if req.hits:
        events: List[EventPoint] = []
        utc_times: List[datetime] = []
        for h in req.hits:
            ts = h.exact_time.astimezone(timezone.utc)
            utc_times.append(ts)
            severity = (
                float(h.severity)
                if h.severity is not None
                else compute_severity(h.aspect, float(h.orb), float(h.orb_limit))
            )
            events.append(EventPoint(ts=ts, score=float(severity)))
        daily = daily_composite(events)
        monthly = monthly_composite(daily)
        window_meta = None
        if utc_times:
            window_meta = {
                "start": min(utc_times).isoformat(),
                "end": max(utc_times).isoformat(),
            }
        return ScoreSeriesResponse(
            daily=[DailyPoint(date=k, score=v) for k, v in daily.items()],
            monthly=[MonthlyPoint(month=k, score=v) for k, v in monthly.items()],
            meta={"count_hits": len(req.hits), "window": window_meta},
        )

    scan = req.scan  # type: ignore[assignment]
    provider = aspects_module._get_provider()
    policy = _resolve_orb_policy_inline_or_id(scan.orb_policy_inline, scan.orb_policy_id)

    start = scan.window.start.astimezone(timezone.utc)
    end = scan.window.end.astimezone(timezone.utc)
    window = TimeWindow(start=start, end=end)

    hits = scan_time_range(
        objects=scan.objects,
        window=window,
        position_provider=provider,
        aspects=scan.aspects,
        harmonics=scan.harmonics or [],
        orb_policy=policy,
        pairs=None,
        step_minutes=scan.step_minutes,
    )
    ranked = rank_hits(hits, profile=None, order_by="time")

    events = [
        EventPoint(ts=h["exact_time"], score=float(h.get("severity") or 0.0))
        for h in ranked
    ]
    daily = daily_composite(events)
    monthly = monthly_composite(daily)

    return ScoreSeriesResponse(
        daily=[DailyPoint(date=k, score=v) for k, v in daily.items()],
        monthly=[MonthlyPoint(month=k, score=v) for k, v in monthly.items()],
        meta={
            "count_hits": len(ranked),
            "window": {"start": start.isoformat(), "end": end.isoformat()},
        },
    )
