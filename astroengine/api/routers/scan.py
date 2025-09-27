"""Scan-related API endpoints for AstroEngine."""

from __future__ import annotations

import inspect
import json
from datetime import UTC, datetime
from pathlib import Path

from typing import Any, Iterable, Sequence
from typing import Literal



from fastapi import APIRouter, HTTPException

from collections.abc import Mapping

from pydantic import AliasChoices, BaseModel, Field, ConfigDict, field_validator, model_validator

from ...detectors.directed_aspects import solar_arc_natal_aspects
from ...detectors.progressed_aspects import progressed_natal_aspects
from ...detectors.returns import solar_lunar_returns
from ...core.transit_engine import scan_transits as transit_aspects
from ...detectors_aspects import AspectHit
from ...ephemeris.swisseph_adapter import SwissEphemerisAdapter
from ...events import ReturnEvent
from ...exporters import write_parquet_canonical, write_sqlite_canonical
from ...exporters_ics import write_ics_canonical


router = APIRouter()



def _to_iso(dt: datetime) -> str:
    utc = dt.astimezone(UTC)
    return utc.isoformat().replace("+00:00", "Z")


def _parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt.astimezone(UTC) if dt.tzinfo else dt.replace(tzinfo=UTC)


class ExportOptions(BaseModel):
    path: str = Field(..., description="Filesystem destination for exported events")
    format: Literal["json", "ics", "parquet", "sqlite"]
    calendar_name: str | None = Field(
        default=None,
        description="Optional calendar name used for ICS exports.",
    )

    @field_validator("path")
    @classmethod
    def _validate_path(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("export path must be provided")
        return value


class TimeWindow(BaseModel):

    """Normalized scan time bounds with legacy payload support."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    natal: datetime = Field(validation_alias=AliasChoices("natal", "natal_ts"))
    start: datetime = Field(validation_alias=AliasChoices("start", "from"))
    end: datetime = Field(validation_alias=AliasChoices("end", "to"))
    natal_inline: dict[str, Any] | None = Field(
        default=None,
        validation_alias="natal_inline",
        exclude=True,
    )

    @model_validator(mode="before")
    def _merge_inline(cls, data: Any) -> Any:
        if isinstance(data, Mapping):
            payload = dict(data)
            inline = payload.get("natal_inline")
            if inline and not payload.get("natal") and not payload.get("natal_ts"):
                ts = inline.get("ts")
                if ts:
                    payload["natal"] = ts
            return payload
        return data

    @field_validator("natal", "start", "end", mode="before")

    def _coerce_datetime(cls, value: Any) -> datetime:
        if isinstance(value, Mapping):
            value = value.get("ts")
        if isinstance(value, datetime):
            return value.astimezone(UTC)
        if isinstance(value, str):
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt.astimezone(UTC) if dt.tzinfo else dt.replace(tzinfo=UTC)
        if isinstance(value, dict):
            ts = value.get("ts")
            if ts:
                dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                return dt.astimezone(UTC) if dt.tzinfo else dt.replace(tzinfo=UTC)
        raise TypeError("expected ISO-8601 timestamp")

    def iso_tuple(self) -> tuple[str, str, str]:
        return _to_iso(self.natal), _to_iso(self.start), _to_iso(self.end)


class TransitScanRequest(TimeWindow):
    method: str | None = Field(default=None, validation_alias="method")
    bodies: Sequence[str] | None = None
    targets: Sequence[str] | None = None
    aspects: Sequence[Any] | None = None
    orb: float = Field(default=1.0, ge=0.0, description="Maximum aspect orb in degrees")
    step_days: float = Field(default=1.0, gt=0.0)
    export: ExportOptions | None = None

    model_config = ConfigDict(extra="ignore")


class ReturnsScanRequest(TimeWindow):
    bodies: Sequence[str] | None = None
    step_days: float | None = None
    export: ExportOptions | None = None

    model_config = ConfigDict(extra="ignore")


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



def _normalize_scan_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a mutable copy of *payload* with inline natal data surfaced."""

    if not isinstance(payload, Mapping):
        raise HTTPException(status_code=422, detail="scan payload must be an object")

    data = dict(payload)
    inline = data.get("natal_inline")
    if isinstance(inline, Mapping):
        ts = inline.get("ts") or inline.get("timestamp")
        if ts and "natal" not in data and "natal_ts" not in data:
            data["natal"] = ts

    return data



def _value_from_hit(hit: AspectHit | Mapping[str, Any], *names: str) -> Any:
    for name in names:
        if isinstance(hit, Mapping) and name in hit and hit[name] is not None:
            return hit[name]
        attr = getattr(hit, name, None)
        if attr is not None:
            return attr
    return None


def _hit_from_aspect(hit: AspectHit | Mapping[str, Any]) -> Hit:
    when_iso = _value_from_hit(hit, "when_iso", "ts")
    moving = _value_from_hit(hit, "moving")
    target = _value_from_hit(hit, "target")
    angle = _value_from_hit(hit, "angle_deg", "aspect")
    orb = _value_from_hit(hit, "orb_abs", "orb")
    orb_allow = _value_from_hit(hit, "orb_allow")
    motion = _value_from_hit(hit, "applying_or_separating")
    if motion is None:
        applying_flag = _value_from_hit(hit, "applying")
        if applying_flag is not None:
            motion = "applying" if applying_flag else "separating"
    family = _value_from_hit(hit, "family")
    lon_moving = _value_from_hit(hit, "lon_moving", "moving_longitude")
    lon_target = _value_from_hit(hit, "lon_target", "target_longitude")
    delta = _value_from_hit(hit, "delta_lambda_deg", "delta")
    offset = _value_from_hit(hit, "offset_deg", "offset")
    metadata = _value_from_hit(hit, "metadata", "meta")
    retrograde = _value_from_hit(hit, "retrograde")

    meta_dict: dict[str, Any] | None
    if isinstance(metadata, Mapping):
        meta_dict = dict(metadata)
    elif metadata is None:
        meta_dict = None
    else:
        meta_dict = {"value": metadata}
    if retrograde is not None:
        meta_dict = dict(meta_dict or {})
        meta_dict.setdefault("retrograde", bool(retrograde))

    return Hit(
        ts=str(when_iso) if when_iso is not None else "",
        moving=str(moving) if moving is not None else "",
        target=str(target) if target is not None else "",
        aspect=int(round(float(angle))) if angle is not None else 0,
        orb=float(abs(float(orb))) if orb is not None else 0.0,
        orb_allow=float(orb_allow) if orb_allow is not None else None,
        motion=str(motion) if motion is not None else None,
        family=str(family) if family is not None else None,
        lon_moving=float(lon_moving) if lon_moving is not None else None,
        lon_target=float(lon_target) if lon_target is not None else None,
        delta=float(delta) if delta is not None else None,
        offset=float(offset) if offset is not None else None,
        metadata=meta_dict,
    )


    normalized: dict[str, Any] = {
        "natal": natal,
        "start": start,
        "end": end,
    }


def _hit_from_return(event: ReturnEvent) -> Hit:
    if hasattr(event, "body"):
        return Hit(
            ts=event.ts,
            moving=event.body,
            target="Return",
            aspect=0,
            orb=0.0,
            metadata={"kind": event.method, "longitude": float(event.longitude)},
        )

    data = event if isinstance(event, Mapping) else event.__dict__
    return Hit(
        ts=str(data.get("ts", "")),
        moving=str(data.get("body", "")),
        target="Return",
        aspect=0,
        orb=0.0,
        metadata={
            "kind": str(data.get("method", "")),
            "longitude": float(data.get("longitude", 0.0) or 0.0),
        },
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


def _normalize_aspects(values: Sequence[Any] | None) -> list[int]:
    if not values:
        return [0, 60, 90, 120, 180]
    resolved: list[int] = []
    for value in values:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            resolved.append(int(round(float(value))))
            continue
        try:
            resolved.append(int(round(float(str(value)))))
        except (TypeError, ValueError):
            continue
    return resolved or [0, 60, 90, 120, 180]


@router.post("/progressions", response_model=ScanResponse)
def api_scan_progressions(payload: dict[str, Any]) -> ScanResponse:
    request_data = _normalize_scan_payload(payload)
    request = TransitScanRequest(**request_data)
    natal, start, end = request.iso_tuple()

    hits = [
        _hit_from_aspect(hit)
        for hit in progressed_natal_aspects(
            natal_ts=natal,
            start_ts=start,
            end_ts=end,
            aspects=_normalize_aspects(request.aspects),
            orb_deg=float(request.orb),
            bodies=request.bodies,
            step_days=request.step_days,
        )
    ]


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

    hits = [
        _hit_from_aspect(hit)
        for hit in solar_arc_natal_aspects(
            natal_ts=natal,
            start_ts=start,
            end_ts=end,
            aspects=_normalize_aspects(request.aspects),
            orb_deg=float(request.orb),
            bodies=request.bodies,
            step_days=request.step_days,
        )
    ]


    export_info = (
        _export_hits(request.export, hits, method="directions")
        if request.export
        else None
    )
    return ScanResponse(method="directions", hits=hits, count=len(hits), export=export_info)


@router.post("/transits", response_model=ScanResponse)

def api_scan_transits(request: TransitScanRequest) -> ScanResponse:
    if (request.method or "").strip().lower() == "transits":
        raise HTTPException(status_code=501, detail="Transit scans are not yet available")
    natal, start, end = request.iso_tuple()
    hits = [
        _hit_from_aspect(hit)
        for hit in transit_aspects(
            natal_ts=natal,
            start_ts=start,
            end_ts=end,
            aspects=request.aspects,
            orb_deg=float(request.orb),
            bodies=request.bodies,
            targets=request.targets,
            step_days=request.step_days,
        )
    ]


    export_info = (
        _export_hits(request.export, hits, method="transits")
        if request.export
        else None
    )

    return ScanResponse(method="transits", hits=hits, count=len(hits), export=export_info)


@router.post("/returns", response_model=ScanResponse)

def api_scan_returns(request: ReturnsScanRequest) -> ScanResponse:
    natal_iso, start_iso, end_iso = request.iso_tuple()
    bodies = list(request.bodies or ["Sun"])

    adapter = SwissEphemerisAdapter.get_default_adapter()
    natal_jd = adapter.julian_day(_parse_iso(natal_iso))
    start_jd = adapter.julian_day(_parse_iso(start_iso))
    end_jd = adapter.julian_day(_parse_iso(end_iso))

    hits: list[Hit] = []
    for body in bodies:
        kind = "solar" if body.lower() == "sun" else "lunar"
        kwargs: dict[str, Any] = {}
        if request.step_days is not None:
            kwargs["step_days"] = request.step_days
        try:
            events = solar_lunar_returns(
                natal_jd,
                start_jd,
                end_jd,
                kind=kind,
                adapter=adapter,
                **kwargs,
            )
        except TypeError:
            events = solar_lunar_returns(
                natal_jd,
                start_jd,
                end_jd,
                kind=kind,
                **kwargs,
            )

        hits.extend(_hit_from_return(event) for event in events)

    export_info = (
        _export_hits(request.export, hits, method="returns")
        if request.export
        else None
    )
    return ScanResponse(method="returns", hits=hits, count=len(hits), export=export_info)


__all__ = [
    "api_scan_progressions",
    "api_scan_directions",
    "api_scan_transits",
    "api_scan_returns",
    "router",
]
