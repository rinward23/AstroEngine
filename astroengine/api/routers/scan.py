from __future__ import annotations

import json
from collections.abc import Iterable, Iterator, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Body, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from ...core.transit_engine import scan_transits
from ...detectors.directed_aspects import solar_arc_natal_aspects
from ...detectors.progressed_aspects import progressed_natal_aspects
from ...detectors.returns import solar_lunar_returns
from ...detectors_aspects import AspectHit
from ...ephemeris import SwissEphemerisAdapter
from ...events import ReturnEvent
from ...exporters import write_parquet_canonical, write_sqlite_canonical
from ...exporters_ics import write_ics_canonical
from ...web.responses import json_response, ndjson_stream

DEFAULT_PAGE_LIMIT = 500
MAX_PAGE_LIMIT = 2000


router = APIRouter()



def _to_iso(dt: datetime) -> str:
    utc = dt.astimezone(UTC)
    return utc.isoformat().replace("+00:00", "Z")


def _parse_iso(value: str) -> datetime:
    return ensure_utc_datetime(value)


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

    model_config = ConfigDict(extra="ignore")

    natal: UtcDateTime = Field(validation_alias=AliasChoices("natal", "natal_ts"))
    start: UtcDateTime = Field(validation_alias=AliasChoices("start", "start_ts", "from"))
    end: UtcDateTime = Field(validation_alias=AliasChoices("end", "end_ts", "to"))

    @field_validator("natal", "start", "end", mode="before")

    def _coerce_datetime(cls, value: Any) -> datetime:
        if isinstance(value, Mapping) and "ts" in value:
            value = value["ts"]
        return ensure_utc_datetime(value)

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
    speed_deg_per_day: float | None = None
    retrograde: bool | None = None
    metadata: dict[str, Any] | None = None


class ScanResponse(BaseModel):
    method: str
    hits: list[Hit]
    count: int
    export: dict[str, Any] | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "description": "count reflects total hits before pagination is applied"
        }
    )



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
    speed = _value_from_hit(hit, "speed_deg_per_day", "speed")

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
    if speed is not None:
        meta_dict = dict(meta_dict or {})
        meta_dict.setdefault("speed_deg_per_day", float(speed))

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
        speed_deg_per_day=float(speed) if speed is not None else None,
        retrograde=bool(retrograde) if retrograde is not None else None,
        metadata=meta_dict,
    )


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
    if hit.speed_deg_per_day is not None:
        meta.setdefault("speed_deg_per_day", hit.speed_deg_per_day)
    if hit.retrograde is not None:
        meta.setdefault("retrograde", hit.retrograde)
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


def _serialize_hit(hit: Hit) -> dict[str, Any]:
    return hit.model_dump(mode="json")


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


def _iter_progression_hits(request: TransitScanRequest) -> Iterator[Hit]:
    natal, start, end = request.iso_tuple()
    yield from (
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
    )


def _iter_direction_hits(request: TransitScanRequest) -> Iterator[Hit]:
    natal, start, end = request.iso_tuple()
    yield from (
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
    )


def _iter_transit_hits(request: TransitScanRequest) -> Iterator[Hit]:
    natal, start, end = request.iso_tuple()
    yield from (
        _hit_from_aspect(hit)
        for hit in scan_transits(
            natal_ts=natal,
            start_ts=start,
            end_ts=end,
            aspects=request.aspects,
            orb_deg=float(request.orb),
            bodies=request.bodies,
            targets=request.targets,
            step_days=request.step_days,
        )
    )


def _iter_return_hits(request: ReturnsScanRequest) -> Iterator[Hit]:
    natal_iso, start_iso, end_iso = request.iso_tuple()
    bodies = list(request.bodies or ["Sun"])

    adapter = SwissEphemerisAdapter.get_default_adapter()
    natal_jd = adapter.julian_day(_parse_iso(natal_iso))
    start_jd = adapter.julian_day(_parse_iso(start_iso))
    end_jd = adapter.julian_day(_parse_iso(end_iso))

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
        for event in events:
            yield _hit_from_return(event)


def _stream_scan_hits(
    method: str,
    hits: Iterable[Hit],
    *,
    offset: int,
    limit: int,
) -> StreamingResponse:
    def iterator() -> Iterator[dict[str, Any]]:
        total = 0
        returned = 0
        yield {
            "event": "metadata",
            "method": method,
            "offset": offset,
            "limit": limit,
        }
        for hit in hits:
            total += 1
            if total <= offset:
                continue
            if returned < limit:
                returned += 1
                yield {"event": "hit", "data": _serialize_hit(hit)}
        yield {
            "event": "summary",
            "method": method,
            "count": total,
            "returned": returned,
            "offset": offset,
            "limit": limit,
        }

    return ndjson_stream(iterator())


@router.post("/progressions", response_model=ScanResponse)
def api_scan_progressions(
    payload: Mapping[str, Any] = Body(..., description="Scan request payload"),
    limit: int = Query(
        DEFAULT_PAGE_LIMIT,
        ge=1,
        le=MAX_PAGE_LIMIT,
        description=(
            f"Maximum number of hits to return (default {DEFAULT_PAGE_LIMIT}, maximum {MAX_PAGE_LIMIT})."
            
        ),
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of hits to skip from the start of the result set.",
    ),
    stream: bool = Query(
        False,
        description="If true, emit NDJSON lines as hits are detected instead of a JSON body.",
    ),
) -> Response | StreamingResponse:
    request_data = _normalize_scan_payload(payload)
    request = TransitScanRequest(**request_data)
    if stream:
        if request.export is not None:
            raise HTTPException(
                status_code=400,
                detail="streaming responses do not support export payloads",
            )
        return _stream_scan_hits(
            "progressions",
            _iter_progression_hits(request),
            offset=offset,
            limit=limit,
        )

    all_hits = list(_iter_progression_hits(request))
    total_hits = len(all_hits)
    page_hits = all_hits[offset : offset + limit]

    export_info = (
        _export_hits(request.export, all_hits, method="progressions")
        if request.export
        else None
    )
    response_model = ScanResponse(
        method="progressions",
        hits=page_hits,
        count=total_hits,
        export=export_info,
    )
    return json_response(response_model.model_dump(mode="json"))


@router.post("/directions", response_model=ScanResponse)
def api_scan_directions(
    payload: Mapping[str, Any] = Body(..., description="Scan request payload"),
    limit: int = Query(
        DEFAULT_PAGE_LIMIT,
        ge=1,
        le=MAX_PAGE_LIMIT,
        description=(
            f"Maximum number of hits to return (default {DEFAULT_PAGE_LIMIT}, maximum {MAX_PAGE_LIMIT})."
            
        ),
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of hits to skip from the start of the result set.",
    ),
    stream: bool = Query(
        False,
        description="If true, emit NDJSON lines as hits are detected instead of a JSON body.",
    ),
) -> Response | StreamingResponse:
    request_data = _normalize_scan_payload(payload)
    request = TransitScanRequest(**request_data)
    if stream:
        if request.export is not None:
            raise HTTPException(
                status_code=400,
                detail="streaming responses do not support export payloads",
            )
        return _stream_scan_hits(
            "directions",
            _iter_direction_hits(request),
            offset=offset,
            limit=limit,
        )

    all_hits = list(_iter_direction_hits(request))
    total_hits = len(all_hits)
    page_hits = all_hits[offset : offset + limit]

    export_info = (
        _export_hits(request.export, all_hits, method="directions")
        if request.export
        else None
    )
    response_model = ScanResponse(
        method="directions",
        hits=page_hits,
        count=total_hits,
        export=export_info,
    )
    return json_response(response_model.model_dump(mode="json"))


@router.post("/transits", response_model=ScanResponse)
def api_scan_transits(
    payload: Mapping[str, Any] = Body(..., description="Scan request payload"),
    limit: int = Query(
        DEFAULT_PAGE_LIMIT,
        ge=1,
        le=MAX_PAGE_LIMIT,
        description=(
            f"Maximum number of hits to return (default {DEFAULT_PAGE_LIMIT}, maximum {MAX_PAGE_LIMIT})."
            
        ),
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of hits to skip from the start of the result set.",
    ),
    stream: bool = Query(
        False,
        description="If true, emit NDJSON lines as hits are detected instead of a JSON body.",
    ),
) -> Response | StreamingResponse:
    request_data = _normalize_scan_payload(payload)
    request = TransitScanRequest(**request_data)

    if (request.method or "").strip().lower() == "transits":
        raise HTTPException(status_code=501, detail="Transit scans are not yet available")
    if stream:
        if request.export is not None:
            raise HTTPException(
                status_code=400,
                detail="streaming responses do not support export payloads",
            )
        return _stream_scan_hits(
            "transits",
            _iter_transit_hits(request),
            offset=offset,
            limit=limit,
        )

    all_hits = list(_iter_transit_hits(request))

    total_hits = len(all_hits)
    page_hits = all_hits[offset : offset + limit]

    export_info = (
        _export_hits(request.export, all_hits, method="transits")
        if request.export
        else None
    )

    response_model = ScanResponse(
        method="transits",
        hits=page_hits,
        count=total_hits,
        export=export_info,
    )

    return json_response(response_model.model_dump(mode="json"))


@router.post("/returns", response_model=ScanResponse)
def api_scan_returns(
    payload: Mapping[str, Any] = Body(..., description="Scan request payload"),
    limit: int = Query(
        DEFAULT_PAGE_LIMIT,
        ge=1,
        le=MAX_PAGE_LIMIT,
        description=(
            f"Maximum number of hits to return (default {DEFAULT_PAGE_LIMIT}, maximum {MAX_PAGE_LIMIT})."
            
        ),
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of hits to skip from the start of the result set.",
    ),
    stream: bool = Query(
        False,
        description="If true, emit NDJSON lines as hits are detected instead of a JSON body.",
    ),
) -> Response | StreamingResponse:
    request_data = _normalize_scan_payload(payload)
    request = ReturnsScanRequest(**request_data)
    if stream:
        if request.export is not None:
            raise HTTPException(
                status_code=400,
                detail="streaming responses do not support export payloads",
            )
        return _stream_scan_hits(
            "returns",
            _iter_return_hits(request),
            offset=offset,
            limit=limit,
        )

    hits = list(_iter_return_hits(request))

    total_hits = len(hits)
    page_hits = hits[offset : offset + limit]

    export_info = (
        _export_hits(request.export, hits, method="returns")
        if request.export
        else None
    )
    response_model = ScanResponse(
        method="returns",
        hits=page_hits,
        count=total_hits,
        export=export_info,
    )
    return json_response(response_model.model_dump(mode="json"))


__all__ = [
    "api_scan_progressions",
    "api_scan_directions",
    "api_scan_transits",
    "api_scan_returns",
    "router",
]
