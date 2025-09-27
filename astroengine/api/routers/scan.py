
"""Scan-related API endpoints for AstroEngine."""

from __future__ import annotations

import inspect
import json
from datetime import UTC, datetime
from pathlib import Path
from collections.abc import Mapping
from typing import Any, Iterable, Literal, Sequence

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator

from ...core.transit_engine import scan_transits
from ...detectors.directed_aspects import solar_arc_natal_aspects
from ...detectors.progressed_aspects import progressed_natal_aspects
from ...detectors.returns import solar_lunar_returns
from ...detectors_aspects import AspectHit
from ...ephemeris.swisseph_adapter import SwissEphemerisAdapter
from ...events import ReturnEvent
from ...exporters import write_parquet_canonical, write_sqlite_canonical
from ...exporters_ics import write_ics_canonical


router = APIRouter()



def _to_iso(dt: datetime) -> str:
    utc = dt.astimezone(UTC)
    return utc.isoformat().replace("+00:00", "Z")


class ExportOptions(BaseModel):
    path: str = Field(..., description="Filesystem destination for exported events")
    format: Literal["json", "ics", "parquet", "sqlite"]
    calendar_name: str | None = Field(
        default=None,
        description="Optional calendar name used for ICS exports.",
    )

    @validator("path")
    def _validate_path(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("export path must be provided")
        return value


class TimeWindow(BaseModel):
    natal: datetime
    start: datetime
    end: datetime

    @validator("natal", "start", "end", pre=True)
    def _coerce_datetime(cls, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value.astimezone(UTC)
        if isinstance(value, str):
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt.astimezone(UTC) if dt.tzinfo else dt.replace(tzinfo=UTC)
        raise TypeError("expected ISO-8601 timestamp")

    def iso_tuple(self) -> tuple[str, str, str]:
        return _to_iso(self.natal), _to_iso(self.start), _to_iso(self.end)


class TransitScanRequest(TimeWindow):
    bodies: Sequence[str] | None = None
    targets: Sequence[str] | None = None
    aspects: Sequence[Any] | None = None
    orb: float = Field(default=1.0, ge=0.0, description="Maximum aspect orb in degrees")
    step_days: float = Field(default=1.0, gt=0.0)
    export: ExportOptions | None = None


class ReturnsScanRequest(TimeWindow):
    bodies: Sequence[str] | None = None
    step_days: float | None = None
    export: ExportOptions | None = None


class Hit(BaseModel):
    ts: str
    moving: str
    target: str
    aspect: int
    orb: float
    orb_allow: float | None = None
    motion: str | None = None
    family: str | None = None
    lon_moving: float | None = None
    lon_target: float | None = None
    delta: float | None = None
    offset: float | None = None
    metadata: dict[str, Any] | None = None


class ScanResponse(BaseModel):
    method: str
    hits: list[Hit]
    count: int
    export: dict[str, Any] | None = None


_ASPECT_NAME_TO_DEGREES: dict[str, float] = {
    "conjunction": 0.0,
    "opposition": 180.0,
    "square": 90.0,
    "trine": 120.0,
    "sextile": 60.0,
    "quincunx": 150.0,
    "semisquare": 45.0,
    "sesquisquare": 135.0,
    "quintile": 72.0,
    "biquintile": 144.0,
}

_DEFAULT_ASPECTS = [0.0, 60.0, 90.0, 120.0, 180.0]


def _attr_lookup(source: object, name: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(name, default)
    return getattr(source, name, default)


def _coerce_motion(source: object) -> str | None:
    motion = _attr_lookup(source, "motion")
    if isinstance(motion, str):
        return motion
    applying_flag = _attr_lookup(source, "applying")
    if applying_flag is True:
        return "applying"
    if applying_flag is False:
        return "separating"
    return _attr_lookup(source, "applying_or_separating")


def _resolve_progression_aspects(values: Sequence[Any] | None) -> list[int]:
    resolved: set[int] = set()
    if values is None:
        return [int(angle) for angle in _DEFAULT_ASPECTS]
    for entry in values:
        if isinstance(entry, (int, float)):
            resolved.add(int(round(float(entry))))
            continue
        if isinstance(entry, str):
            token = entry.strip().lower()
            if token in _ASPECT_NAME_TO_DEGREES:
                resolved.add(int(round(_ASPECT_NAME_TO_DEGREES[token])))
                continue
            try:
                resolved.add(int(round(float(token))))
            except (TypeError, ValueError):
                continue
    return sorted(resolved) if resolved else [int(angle) for angle in _DEFAULT_ASPECTS]


def _normalize_scan_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):  # pragma: no cover - FastAPI guards
        raise HTTPException(status_code=400, detail="scan payload must be a JSON object")

    data = dict(payload)
    natal = data.get("natal")
    if natal is None:
        inline = data.get("natal_inline")
        if isinstance(inline, Mapping):
            natal = inline.get("ts")

    start = data.get("start") or data.get("from")
    end = data.get("end") or data.get("to")
    if not natal or not start or not end:
        raise HTTPException(
            status_code=422,
            detail="natal, start, and end timestamps are required",
        )

    normalized: dict[str, Any] = {
        "natal": natal,
        "start": start,
        "end": end,
    }

    step_days = data.get("step_days")
    if step_days is None and "step_minutes" in data:
        try:
            step_days = float(data["step_minutes"]) / (24.0 * 60.0)
        except (TypeError, ValueError):
            step_days = None
    if step_days is not None:
        normalized["step_days"] = step_days

    for key in ("bodies", "targets", "aspects", "orb", "export"):
        value = data.get(key)
        if value is not None:
            normalized[key] = value

    return normalized


def _hit_from_aspect(hit: AspectHit | Mapping[str, Any] | object) -> Hit:
    if isinstance(hit, AspectHit):
        meta_source = getattr(hit, "metadata", None)
        return Hit(
            ts=hit.when_iso,
            moving=hit.moving,
            target=hit.target,
            aspect=int(round(hit.angle_deg)),
            orb=float(abs(hit.orb_abs)),
            orb_allow=float(hit.orb_allow) if hit.orb_allow is not None else None,
            motion=hit.applying_or_separating,
            family=hit.family,
            lon_moving=float(hit.lon_moving) if hit.lon_moving is not None else None,
            lon_target=float(hit.lon_target) if hit.lon_target is not None else None,
            delta=float(hit.delta_lambda_deg) if hit.delta_lambda_deg is not None else None,
            offset=float(hit.offset_deg) if hit.offset_deg is not None else None,
            metadata=dict(meta_source or {}),
        )

    getter = lambda key, default=None: _attr_lookup(hit, key, default)
    ts = getter("when_iso") or getter("ts")
    moving = getter("moving") or getter("a")
    target = getter("target") or getter("b")
    aspect_value = getter("aspect") or getter("angle_deg") or getter("angle")
    try:
        aspect = int(round(float(aspect_value))) if aspect_value is not None else 0
    except (TypeError, ValueError):
        aspect = 0
    orb_value = getter("orb") or getter("orb_abs") or getter("offset")
    try:
        orb = float(abs(orb_value)) if orb_value is not None else 0.0
    except (TypeError, ValueError):
        orb = 0.0
    orb_allow_val = getter("orb_allow") or getter("orb_limit")
    try:
        orb_allow = float(orb_allow_val) if orb_allow_val is not None else None
    except (TypeError, ValueError):
        orb_allow = None
    lon_moving = getter("lon_moving")
    lon_target = getter("lon_target")
    delta_val = getter("delta") or getter("delta_lambda_deg")
    try:
        delta = float(delta_val) if delta_val is not None else None
    except (TypeError, ValueError):
        delta = None
    offset_val = getter("offset") or getter("offset_deg")
    try:
        offset = float(offset_val) if offset_val is not None else None
    except (TypeError, ValueError):
        offset = None

    meta: dict[str, Any] = {}
    retrograde = getter("retrograde")
    if retrograde is not None:
        meta["retrograde"] = retrograde
    method = getter("method")
    if method is not None:
        meta["method"] = method
    family = getter("family") or getter("kind")

    return Hit(
        ts=str(ts) if ts is not None else "",
        moving=str(moving) if moving is not None else "",
        target=str(target) if target is not None else "",
        aspect=aspect,
        orb=orb,
        orb_allow=orb_allow,
        motion=_coerce_motion(hit),
        family=str(family) if family is not None else None,
        lon_moving=float(lon_moving) if lon_moving is not None else None,
        lon_target=float(lon_target) if lon_target is not None else None,
        delta=delta,
        offset=offset,
        metadata=meta or None,
    )


def _hit_from_return(event: ReturnEvent) -> Hit:
    return Hit(
        ts=event.ts,
        moving=event.body,
        target="Return",
        aspect=0,
        orb=0.0,
        metadata={"kind": event.method, "longitude": float(event.longitude)},
    )


def _hit_to_canonical(hit: Hit) -> dict[str, Any]:
    meta = dict(hit.metadata or {})
    if hit.family and "family" not in meta:
        meta["family"] = hit.family
    if hit.motion and "motion" not in meta:
        meta["motion"] = hit.motion
    if hit.delta is not None:
        meta.setdefault("delta", hit.delta)
    if hit.offset is not None:
        meta.setdefault("offset", hit.offset)
    if hit.lon_moving is not None:
        meta.setdefault("lon_moving", hit.lon_moving)
    if hit.lon_target is not None:
        meta.setdefault("lon_target", hit.lon_target)
    return {
        "ts": hit.ts,
        "moving": hit.moving,
        "target": hit.target,
        "aspect": str(hit.aspect),
        "orb": hit.orb,
        "orb_allow": hit.orb_allow,
        "applying": hit.motion == "applying" if hit.motion else None,
        "score": meta.get("score", 0.0),
        "meta": meta,
    }


def _export_hits(options: ExportOptions, hits: Iterable[Hit], *, method: str) -> dict[str, Any]:
    canonical = [_hit_to_canonical(hit) for hit in hits]
    path = Path(options.path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fmt = options.format

    if fmt == "json":
        path.write_text(json.dumps(canonical, indent=2), encoding="utf-8")
    elif fmt == "ics":
        calendar_name = options.calendar_name or f"AstroEngine {method.title()}"
        write_ics_canonical(path, canonical, calendar_name=calendar_name)
    elif fmt == "parquet":
        write_parquet_canonical(str(path), canonical)
    elif fmt == "sqlite":
        write_sqlite_canonical(str(path), canonical)
    else:  # pragma: no cover - guarded by validator
        raise HTTPException(status_code=400, detail="Unsupported export format")

    return {"path": str(path), "format": fmt, "count": len(canonical)}


@router.post("/progressions", response_model=ScanResponse)
def api_scan_progressions(payload: dict[str, Any]) -> ScanResponse:
    request_data = _normalize_scan_payload(payload)
    request = TransitScanRequest(**request_data)
    natal, start, end = request.iso_tuple()
    aspects = _resolve_progression_aspects(request.aspects)
    hits_raw = progressed_natal_aspects(
        natal_ts=natal,
        start_ts=start,
        end_ts=end,
        aspects=aspects,
        orb_deg=float(request.orb),
        bodies=request.bodies,
        step_days=float(request.step_days),
    )
    hits = [_hit_from_aspect(item) for item in hits_raw]

    export_info = (
        _export_hits(request.export, hits, method="progressions")
        if request.export
        else None
    )
    return ScanResponse(method="progressions", hits=hits, count=len(hits), export=export_info)


@router.post("/directions", response_model=ScanResponse)
def api_scan_directions(payload: dict[str, Any]) -> ScanResponse:
    request_data = _normalize_scan_payload(payload)
    request = TransitScanRequest(**request_data)
    natal, start, end = request.iso_tuple()
    aspects = _resolve_progression_aspects(request.aspects)
    hits_raw = solar_arc_natal_aspects(
        natal_ts=natal,
        start_ts=start,
        end_ts=end,
        aspects=aspects,
        orb_deg=float(request.orb),
        bodies=request.bodies,
        step_days=float(request.step_days),
    )
    hits = [_hit_from_aspect(item) for item in hits_raw]

    export_info = (
        _export_hits(request.export, hits, method="directions")
        if request.export
        else None
    )
    return ScanResponse(method="directions", hits=hits, count=len(hits), export=export_info)


@router.post("/transits", response_model=ScanResponse)
def api_scan_transits(payload: dict[str, Any]) -> ScanResponse:
    if payload.get("method") == "transits" and "natal" not in payload:
        raise HTTPException(status_code=501, detail="Legacy transit payloads are unsupported")

    request_data = _normalize_scan_payload(payload)
    request = TransitScanRequest(**request_data)
    natal, start, end = request.iso_tuple()
    aspect_hits = scan_transits(
        natal,
        start,
        end,
        aspects=request.aspects,
        orb_deg=request.orb,
        bodies=request.bodies,
        targets=request.targets,
        step_days=request.step_days,
    )

    hits = [_hit_from_aspect(item) for item in aspect_hits]
    export_info = (
        _export_hits(request.export, hits, method="transits")
        if request.export
        else None
    )
    return ScanResponse(method="transits", hits=hits, count=len(hits), export=export_info)


@router.post("/returns", response_model=ScanResponse)
def api_scan_returns(payload: dict[str, Any]) -> ScanResponse:
    request_data = _normalize_scan_payload(payload)
    request = ReturnsScanRequest(**request_data)
    bodies = list(request.bodies or ["Sun"])

    adapter = SwissEphemerisAdapter.get_default_adapter()
    natal_jd = adapter.julian_day(request.natal)
    start_jd = adapter.julian_day(request.start)
    end_jd = adapter.julian_day(request.end)

    hits: list[Hit] = []
    for body in bodies:
        kind = "solar" if str(body).lower() == "sun" else "lunar"
        sig = inspect.signature(solar_lunar_returns)
        params = sig.parameters
        kwargs: dict[str, Any] = {"kind": kind}
        if "step_days" in params and request.step_days is not None:
            kwargs["step_days"] = request.step_days
        if "adapter" in params:
            kwargs["adapter"] = adapter
        events = solar_lunar_returns(
            natal_jd,
            start_jd,
            end_jd,
            **kwargs,
        )
        hits.extend(_hit_from_return(event) for event in events)

    export_info = (
        _export_hits(request.export, hits, method="returns")
        if request.export
        else None
    )
    return ScanResponse(method="returns", hits=hits, count=len(hits), export=export_info)

