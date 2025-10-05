"""REST router exposing the aspect search endpoint."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from typing import Any, Callable, Dict


from fastapi import APIRouter, HTTPException, Request

from app.schemas.aspects import (
    AspectHit,
    AspectSearchRequest,
    AspectSearchResponse,
    DayBin,
    Paging,
)
from astroengine.core.aspects_plus.aggregate import day_bins, paginate, rank_hits
from astroengine.core.aspects_plus.provider_wrappers import (
    PositionProvider,
    cached_position_provider,
)
from astroengine.core.aspects_plus.scan import TimeWindow, scan_time_range

try:  # Optional repositories for policy lookup
    from app.repo.orb_policies import OrbPolicyRepo  # type: ignore
    from app.db.session import session_scope  # type: ignore
except Exception:  # pragma: no cover
    OrbPolicyRepo = None  # type: ignore
    session_scope = None  # type: ignore

router = APIRouter(prefix="", tags=["Plus"])
__all__ = ["router", "configure_position_provider", "clear_position_provider"]

# -----------------------------------------------------------------------------
# Position provider injection
# -----------------------------------------------------------------------------
position_provider: Callable[[datetime], Dict[str, float]] | None = None
_cached: tuple[
    Callable[[datetime], Dict[str, float]],
    Callable[[datetime], Dict[str, float]],
] | None = None



def configure_position_provider(provider: PositionProvider) -> PositionProvider:
    """Register a callable that returns ecliptic longitudes for aspect scans.

    The cache wrapper is reset so repeated calls always see fresh configuration,
    which is important for tests that swap demo providers in and out.
    """

    global position_provider, _cached
    position_provider = provider
    _cached = None
    return provider


def clear_position_provider() -> None:
    """Remove any previously configured provider and reset the memoized wrapper."""

    global position_provider, _cached
    position_provider = None
    _cached = None


def _get_provider() -> PositionProvider:
    global position_provider, _cached

    if position_provider is None:

        _cached = None

        def _stub(_ts: datetime):

            raise RuntimeError("position_provider not configured")

        return _stub

    cached_entry = _cached
    if cached_entry is None or cached_entry[0] is not position_provider:

        res_min = int(os.getenv("ASTRO_CACHE_RES_MIN", "5"))
        ttl_sec = float(os.getenv("ASTRO_CACHE_TTL_SEC", "600"))
        wrapper = cached_position_provider(
            position_provider,
            resolution_minutes=res_min,
            ttl_seconds=ttl_sec,
        )
        _cached = (position_provider, wrapper)
        cached_entry = _cached
    return cached_entry[1]


# -----------------------------------------------------------------------------
# Orb policy resolution
# -----------------------------------------------------------------------------
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


def _resolve_orb_policy(req: AspectSearchRequest) -> Dict[str, Any]:
    if req.orb_policy_inline is not None:
        return req.orb_policy_inline.model_dump()
    if req.orb_policy_id is not None:
        if OrbPolicyRepo is None or session_scope is None:
            raise HTTPException(
                status_code=400,
                detail="orb_policy_id requires DB repos; provide orb_policy_inline instead",
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


# -----------------------------------------------------------------------------
# Endpoint
# -----------------------------------------------------------------------------
@router.post(
    "/aspects/search",
    response_model=AspectSearchResponse,
    summary="Search aspects over a time window",
    description=(
        "Scans a time range for aspect hits across object pairs with optional harmonics "
        "and adaptive orb policy."
    ),
    operation_id="plus_aspects_search",
)
def aspects_search(req: AspectSearchRequest, request: Request):
    provider = _get_provider()
    policy = _resolve_orb_policy(req)

    settings = getattr(request.app.state, "settings", None)
    antiscia_cfg = getattr(settings, "antiscia", None) if settings is not None else None
    antiscia_enabled = bool(getattr(antiscia_cfg, "enabled", False)) if antiscia_cfg else False
    antiscia_orb = getattr(antiscia_cfg, "orb", None) if antiscia_cfg else None

    start = req.window.start.astimezone(timezone.utc)
    end = req.window.end.astimezone(timezone.utc)
    window = TimeWindow(start=start, end=end)

    hits = scan_time_range(
        objects=req.objects,
        window=window,
        position_provider=provider,
        aspects=req.aspects,
        harmonics=req.harmonics or [],
        orb_policy=policy,
        pairs=req.pairs,
        step_minutes=req.step_minutes,
        include_antiscia=antiscia_enabled,
        antiscia_orb=antiscia_orb,
    )

    ranked = rank_hits(hits, profile=None, order_by=req.order_by)
    page, total = paginate(ranked, limit=req.limit, offset=req.offset)

    dto_hits = [
        AspectHit(
            a=h["a"],
            b=h["b"],
            aspect=h["aspect"],
            harmonic=h.get("harmonic"),
            exact_time=h["exact_time"],
            orb=h["orb"],
            orb_limit=h["orb_limit"],
            severity=h.get("severity"),
            meta=h.get("meta", {}),
        )
        for h in page
    ]

    bins = day_bins(ranked)
    dto_bins = [
        DayBin(
            date=datetime.strptime(b["date"], "%Y-%m-%d").date(),
            count=b["count"],
            score=b.get("score"),
        )
        for b in bins
    ]

    return AspectSearchResponse(
        hits=dto_hits,
        bins=dto_bins,
        paging=Paging(limit=req.limit, offset=req.offset, total=total),
    )
