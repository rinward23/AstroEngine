"""REST router exposing transit score series aggregation."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List

from fastapi import APIRouter, HTTPException

from app.routers import aspects as aspects_router
from app.schemas.aspects import AspectHit, AspectSearchRequest
from app.schemas.series import (
    DailyScore,
    MonthlyScore,
    ScoreSeriesMeta,
    ScoreSeriesRequest,
    ScoreSeriesResponse,
    ScoreSeriesScan,
    TimeWindow,
)
from astroengine.core.aspects_plus.aggregate import rank_hits
from astroengine.core.aspects_plus.scan import TimeWindow as ScanTimeWindow, scan_time_range

router = APIRouter(prefix="", tags=["Plus"])


def _ensure_provider():
    try:
        return aspects_router._get_provider()
    except AttributeError as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=500, detail="position provider unavailable") from exc


def _scan_hits(scan: ScoreSeriesScan) -> List[AspectHit]:
    provider = _ensure_provider()
    stub_request = AspectSearchRequest(
        objects=scan.objects,
        aspects=scan.aspects,
        harmonics=scan.harmonics,
        window=scan.window,
        pairs=scan.pairs,
        orb_policy_id=scan.orb_policy_id,
        orb_policy_inline=scan.orb_policy_inline,
        step_minutes=scan.step_minutes,
        limit=5000,
        offset=0,
        order_by="time",
    )
    policy = aspects_router._resolve_orb_policy(stub_request)

    start = scan.window.start.astimezone(timezone.utc)
    end = scan.window.end.astimezone(timezone.utc)
    scan_window = ScanTimeWindow(start=start, end=end)

    raw_hits = scan_time_range(
        objects=scan.objects,
        window=scan_window,
        position_provider=provider,
        aspects=scan.aspects,
        harmonics=scan.harmonics or [],
        orb_policy=policy,
        pairs=scan.pairs,
        step_minutes=scan.step_minutes,
    )
    ranked = rank_hits(raw_hits, profile=None, order_by="time")
    return [
        AspectHit(
            a=item["a"],
            b=item["b"],
            aspect=item["aspect"],
            harmonic=item.get("harmonic"),
            exact_time=item["exact_time"],
            orb=float(item["orb"]),
            orb_limit=float(item["orb_limit"]),
            severity=item.get("severity"),
            meta=item.get("meta", {}),
        )
        for item in ranked
    ]


def _aggregate_daily(hits: Iterable[AspectHit]) -> List[DailyScore]:
    buckets: Dict[datetime, List[float]] = defaultdict(list)
    for hit in hits:
        ts = hit.exact_time
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        else:
            ts = ts.astimezone(timezone.utc)
        if hit.severity is not None:
            buckets[datetime(ts.year, ts.month, ts.day, tzinfo=timezone.utc)].append(float(hit.severity))
    daily: List[DailyScore] = []
    for key in sorted(buckets):
        scores = buckets[key]
        avg = sum(scores) / len(scores) if scores else None
        daily.append(DailyScore(date=key.date(), score=avg))
    return daily


def _aggregate_monthly(daily: Iterable[DailyScore]) -> List[MonthlyScore]:
    buckets: Dict[str, List[float]] = defaultdict(list)
    for entry in daily:
        if entry.score is None:
            continue
        key = entry.date.strftime("%Y-%m")
        buckets[key].append(float(entry.score))
    monthly: List[MonthlyScore] = []
    for key in sorted(buckets):
        scores = buckets[key]
        avg = sum(scores) / len(scores) if scores else None
        monthly.append(MonthlyScore(month=key, score=avg))
    return monthly


def _infer_window(request: ScoreSeriesRequest, hits: List[AspectHit]) -> TimeWindow | None:
    if request.scan is not None:
        return request.scan.window
    times = [hit.exact_time for hit in hits if isinstance(hit.exact_time, datetime)]
    if not times:
        return None
    start = min(times)
    end = max(times)
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    else:
        start = start.astimezone(timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    else:
        end = end.astimezone(timezone.utc)
    if end <= start:
        end = start + timedelta(minutes=1)
    return TimeWindow(start=start, end=end)


@router.post(
    "/transits/score-series",
    response_model=ScoreSeriesResponse,
    summary="Daily & monthly composite severity",
    description="Aggregate severity by UTC day and month from either a fresh scan or a provided list of hits.",
    operation_id="plus_score_series",
)
def score_series(request: ScoreSeriesRequest) -> ScoreSeriesResponse:
    if request.hits is not None:
        hits = request.hits
    elif request.scan is not None:
        hits = _scan_hits(request.scan)
    else:  # pragma: no cover - guarded by model validator
        raise HTTPException(status_code=400, detail="Either scan or hits must be provided")

    daily = _aggregate_daily(hits)
    monthly = _aggregate_monthly(daily)
    window = _infer_window(request, hits)
    meta = ScoreSeriesMeta(count_hits=len(hits), window=window)
    return ScoreSeriesResponse(daily=daily, monthly=monthly, meta=meta)


__all__ = ["router", "score_series"]
