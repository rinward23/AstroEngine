from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import Histogram

from app.schemas.rel import (
    CompositeDavisonRequest,
    CompositeMidpointRequest,
    CompositeResponse,
    SynastryGrid,
    SynastryHit,
    SynastryRequest,
    SynastryResponse,
)
from astroengine.cache.relationship import (
    build_default_relationship_cache,
    canonicalize_composite_payload,
    canonicalize_davison_payload,
    canonicalize_synastry_payload,
)
from astroengine.cache.relationship.layer import CacheEntry
from astroengine.utils import json as json_utils
from core.rel_plus import (
    composite_midpoint_positions,
    davison_positions,
    geodesic_midpoint,
    midpoint_time,
)
from core.rel_plus.synastry import synastry_grid, synastry_interaspects

try:  # pragma: no cover - optional dependency path

    from app.db.session import session_scope  # type: ignore
    from app.repo.orb_policies import OrbPolicyRepo  # type: ignore
except Exception:  # pragma: no cover - fall back to inline policies only
    OrbPolicyRepo = None  # type: ignore
    session_scope = None  # type: ignore

from app.routers import aspects as aspects_module

router = APIRouter(prefix="", tags=["Plus"])
_LOGGER = logging.getLogger(__name__)

_SYN_CACHE = build_default_relationship_cache(
    "syn",
    int(os.getenv("CACHE_TTL_SYN", str(24 * 60 * 60))),
)
_COMP_CACHE = build_default_relationship_cache(
    "comp",
    int(os.getenv("CACHE_TTL_COMP", str(7 * 24 * 60 * 60))),
)
_DAV_CACHE = build_default_relationship_cache(
    "dav",
    int(os.getenv("CACHE_TTL_DAV", str(7 * 24 * 60 * 60))),
)

_LATENCY = {
    "synastry": Histogram(
        "synastry_latency_ms",
        "Latency for synastry computations (ms)",
        buckets=(5, 10, 20, 40, 60, 80, 100, 150, 200, 300, 500),
    ),
    "composite": Histogram(
        "composite_latency_ms",
        "Latency for composite midpoint computations (ms)",
        buckets=(5, 10, 20, 40, 80, 160, 320, 640),
    ),
    "davison": Histogram(
        "davison_latency_ms",
        "Latency for Davison computations (ms)",
        buckets=(10, 20, 40, 80, 160, 320, 640, 1280),
    ),
}

_PAYLOAD_BYTES = Histogram(
    "relationship_payload_bytes",
    "Serialized payload size for relationship endpoints",
    buckets=(128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768),
    labelnames=("endpoint",),
)


def _json_payload_size(body: Any) -> int:
    return len(json_utils.dumps(body))


def _etag_matches(request: Request, etag: str) -> bool:
    if_none_match = request.headers.get("if-none-match")
    if not if_none_match:
        return False
    tags = {tag.strip('"') for tag in if_none_match.split(",") if tag.strip()}
    return etag in tags


def _respond_from_entry(
    entry: CacheEntry,
    *,
    etag: str,
    response: Response,
    endpoint: str,
    cache_status: str,
) -> JSONResponse:
    headers = dict(entry.headers)
    headers.setdefault("Content-Type", "application/json")
    headers["ETag"] = etag
    headers["X-Cache-Status"] = cache_status
    for key, value in headers.items():
        response.headers[key] = value
    payload_bytes = _json_payload_size(entry.body)
    _PAYLOAD_BYTES.labels(endpoint=endpoint).observe(payload_bytes)
    return JSONResponse(content=entry.body, status_code=entry.status_code, headers=response.headers)


def _log_cache(endpoint: str, status: str, key: str) -> None:
    _LOGGER.info(
        "relationship_request",
        extra={
            "cache_status": status,
            "cache_key_prefix": key.split(":")[0],
            "endpoint": endpoint,
        },
    )


def _serve_cached_response(
    *,
    cache,
    key: str,
    request: Request,
    response: Response,
    endpoint: str,
    latency_metric: Histogram,
    compute_fn: Callable[[], tuple[Any, int, dict[str, str]]],
):
    start = time.perf_counter()
    outcome = cache.get(key)
    response.headers["ETag"] = outcome.etag
    if outcome.entry and _etag_matches(request, outcome.etag):
        latency_metric.observe((time.perf_counter() - start) * 1000.0)
        response.status_code = 304
        response.headers["X-Cache-Status"] = "etag"
        _log_cache(endpoint, "etag", key)
        return Response(status_code=304, headers=dict(response.headers))
    if outcome.entry:
        latency_metric.observe((time.perf_counter() - start) * 1000.0)
        _log_cache(endpoint, outcome.source, key)
        return _respond_from_entry(
            outcome.entry,
            etag=outcome.etag,
            response=response,
            endpoint=endpoint,
            cache_status=outcome.source,
        )

    def _compute_entry() -> CacheEntry:
        body, status_code, headers = compute_fn()
        hdrs = dict(headers or {})
        hdrs.setdefault("Content-Type", "application/json")
        return CacheEntry(
            body=body,
            status_code=status_code,
            headers=hdrs,
            created_at=time.time(),
        )

    outcome = cache.with_singleflight(key, _compute_entry)
    latency_metric.observe((time.perf_counter() - start) * 1000.0)
    _log_cache(endpoint, outcome.source, key)
    if not outcome.entry:
        raise RuntimeError("Cache compute returned no entry")
    return _respond_from_entry(
        outcome.entry,
        etag=outcome.etag,
        response=response,
        endpoint=endpoint,
        cache_status=outcome.source,
    )

DEFAULT_POLICY: dict[str, Any] = {
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


def _resolve_orb_policy(req: SynastryRequest) -> dict[str, Any]:
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
def synastry_compute(req: SynastryRequest, request: Request, response: Response):
    policy = _resolve_orb_policy(req)
    canonical = canonicalize_synastry_payload(
        req.pos_a,
        req.pos_b,
        req.aspects,
        policy,
    )

    def _compute() -> tuple[Any, int, dict[str, str]]:
        hits_list = synastry_interaspects(
            req.pos_a,
            req.pos_b,
            req.aspects,
            policy,
        )
        hits = [SynastryHit(**h) for h in hits_list]
        grid = SynastryGrid(counts=synastry_grid(hits_list))
        payload = SynastryResponse(hits=hits, grid=grid).model_dump(mode="json")
        return payload, 200, {}

    return _serve_cached_response(
        cache=_SYN_CACHE,
        key=canonical.digest,
        request=request,
        response=response,
        endpoint="synastry",
        latency_metric=_LATENCY["synastry"],
        compute_fn=_compute,
    )


@router.post(
    "/composites/midpoint",
    response_model=CompositeResponse,
    summary="Midpoint Composite positions",
    description="Circular midpoints of longitudes for the requested objects.",
)

def composites_midpoint(req: CompositeMidpointRequest, request: Request, response: Response):
    canonical = canonicalize_composite_payload(req.pos_a, req.pos_b, req.objects)

    def _compute() -> tuple[Any, int, dict[str, str]]:
        pos = composite_midpoint_positions(req.pos_a, req.pos_b, req.objects)
        payload = CompositeResponse(positions=pos, meta={"method": "midpoint"}).model_dump(
            mode="json"
        )
        return payload, 200, {}

    return _serve_cached_response(
        cache=_COMP_CACHE,
        key=canonical.digest,
        request=request,
        response=response,
        endpoint="composite",
        latency_metric=_LATENCY["composite"],
        compute_fn=_compute,
    )



@router.post(
    "/composites/davison",
    response_model=CompositeResponse,
    summary="Davison Composite positions (time midpoint)",
    description=(
        "Computes body longitudes at the UTC time midpoint between two datetimes using the configured ephemeris provider."
    ),
)

def composites_davison(req: CompositeDavisonRequest, request: Request, response: Response):
    canonical = canonicalize_davison_payload(

        req.objects,
        req.dt_a,
        req.dt_b,
        lat_a=req.lat_a,
        lon_a=req.lon_a,
        lat_b=req.lat_b,
        lon_b=req.lon_b,
    )


    def _compute() -> tuple[Any, int, dict[str, str]]:
        provider = aspects_module._get_provider()
        pos = davison_positions(
            req.objects,
            req.dt_a,
            req.dt_b,
            provider,
            lat_a=req.lat_a,
            lon_a=req.lon_a,
            lat_b=req.lat_b,
            lon_b=req.lon_b,
        )
        midpoint = midpoint_time(req.dt_a, req.dt_b)
        mid_lat, mid_lon = geodesic_midpoint(req.lat_a, req.lon_a, req.lat_b, req.lon_b)
        payload = CompositeResponse(
            positions=pos,
            meta={
                "method": "davison",
                "midpoint_time": midpoint.isoformat(),
                "midpoint_location": {"lat": mid_lat, "lon": mid_lon},
            },
        ).model_dump(mode="json")
        return payload, 200, {}

    return _serve_cached_response(
        cache=_DAV_CACHE,
        key=canonical.digest,
        request=request,
        response=response,
        endpoint="davison",
        latency_metric=_LATENCY["davison"],
        compute_fn=_compute,

    )
