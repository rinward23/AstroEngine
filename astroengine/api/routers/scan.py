
"""Scan-related API endpoints for AstroEngine."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping, Sequence

from fastapi import APIRouter, HTTPException
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, validator

from ...core.transit_engine import scan_transits
from ...detectors.directions import solar_arc_directions
from ...detectors.progressions import secondary_progressions
from ...detectors.returns import solar_lunar_returns as _solar_lunar_returns
from ...ephemeris import SwissEphemerisAdapter
from ...events import DirectionEvent, ProgressionEvent, ReturnEvent
from ...exporters import write_parquet_canonical, write_sqlite_canonical
from ...exporters_ics import write_ics_canonical
from ...detectors_aspects import AspectHit


router = APIRouter()


def progressed_natal_aspects(
    natal_iso: str,
    start_iso: str,
    end_iso: str,
    *,
    bodies: Sequence[str] | None = None,
    step_days: float = 30.0,
):
    return secondary_progressions(
        natal_iso,
        start_iso,
        end_iso,
        bodies=bodies,
        step_days=step_days,
    )


def solar_arc_natal_aspects(
    natal_iso: str,
    start_iso: str,
    end_iso: str,
    *,
    bodies: Sequence[str] | None = None,
):
    return solar_arc_directions(
        natal_iso,
        start_iso,
        end_iso,
        bodies=bodies,
    )


def solar_lunar_returns(
    natal_jd: float,
    start_jd: float,
    end_jd: float,
    *,
    kind: str,
    step_days: float | None = None,
    adapter: SwissEphemerisAdapter | None = None,
):
    return _solar_lunar_returns(
        natal_jd,
        start_jd,
        end_jd,
        kind=kind,
        step_days=step_days,
        adapter=adapter,
    )



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
    natal: datetime = Field(
        ...,
        validation_alias=AliasChoices("natal", "natal_inline"),
    )
    start: datetime = Field(
        ...,
        validation_alias=AliasChoices("start", "from"),
    )
    end: datetime = Field(
        ...,
        validation_alias=AliasChoices("end", "to"),
    )

    model_config = ConfigDict(extra="ignore")

    @validator("natal", "start", "end", pre=True)
    def _coerce_datetime(cls, value: Any) -> datetime:
        if isinstance(value, Mapping):
            value = value.get("ts")
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


def _hit_from_aspect(hit: AspectHit) -> Hit:
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
    )


def _hit_from_progression(event: ProgressionEvent) -> list[Hit]:
    if hasattr(event, "positions"):
        payload: list[Hit] = []
        for body, longitude in event.positions.items():
            payload.append(
                Hit(
                    ts=event.ts,
                    moving=str(body),
                    target="Progression",
                    aspect=0,
                    orb=0.0,
                    metadata={
                        "method": getattr(event, "method", "progressions"),
                        "longitude": float(longitude),
                    },
                )
            )
        return payload

    data = event if isinstance(event, Mapping) else event.__dict__
    return [
        Hit(
            ts=str(data.get("when_iso", data.get("ts", ""))),
            moving=str(data.get("moving", "")),
            target=str(data.get("target", "")),
            aspect=int(data.get("aspect", 0) or 0),
            orb=float(data.get("orb", 0.0) or 0.0),
            metadata={"method": "progressions"},
        )
    ]


def _hit_from_direction(event: DirectionEvent) -> list[Hit]:
    if hasattr(event, "positions"):
        payload: list[Hit] = []
        for body, longitude in event.positions.items():
            payload.append(
                Hit(
                    ts=event.ts,
                    moving=str(body),
                    target="Direction",
                    aspect=0,
                    orb=0.0,
                    metadata={
                        "method": getattr(event, "method", "directions"),
                        "longitude": float(longitude),
                        "arc_degrees": float(getattr(event, "arc_degrees", 0.0)),
                    },
                )
            )
        return payload

    data = event if isinstance(event, Mapping) else event.__dict__
    return [
        Hit(
            ts=str(data.get("when_iso", data.get("ts", ""))),
            moving=str(data.get("moving", "")),
            target=str(data.get("target", "")),
            aspect=int(data.get("aspect", 0) or 0),
            orb=float(data.get("orb", 0.0) or 0.0),
            metadata={
                "method": "directions",
                "motion": data.get("applying_or_separating"),
            },
        )
    ]


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


@router.post("/progressions", response_model=ScanResponse)
def api_scan_progressions(request: TransitScanRequest) -> ScanResponse:
    natal, start, end = request.iso_tuple()
    events = progressed_natal_aspects(
        natal_iso=natal,
        start_iso=start,
        end_iso=end,
        bodies=request.bodies,
        step_days=request.step_days,
    )

    hits: list[Hit] = []
    for event in events:
        hits.extend(_hit_from_progression(event))

    export_info = (
        _export_hits(request.export, hits, method="progressions")
        if request.export
        else None
    )
    return ScanResponse(method="progressions", hits=hits, count=len(hits), export=export_info)


@router.post("/directions", response_model=ScanResponse)
def api_scan_directions(request: TransitScanRequest) -> ScanResponse:
    natal, start, end = request.iso_tuple()
    events = solar_arc_natal_aspects(
        natal_iso=natal,
        start_iso=start,
        end_iso=end,
        bodies=request.bodies,
    )

    hits: list[Hit] = []
    for event in events:
        hits.extend(_hit_from_direction(event))

    export_info = (
        _export_hits(request.export, hits, method="directions")
        if request.export
        else None
    )
    return ScanResponse(method="directions", hits=hits, count=len(hits), export=export_info)


@router.post("/transits", response_model=ScanResponse)
def api_scan_transits(request: TransitScanRequest) -> ScanResponse:
    natal, start, end = request.iso_tuple()
    if not request.bodies or not request.targets or not request.aspects:
        raise HTTPException(
            status_code=501,
            detail="transit scanning requires bodies, targets, and aspects",
        )
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
def api_scan_returns(request: ReturnsScanRequest) -> ScanResponse:
    natal, start, end = request.iso_tuple()
    bodies = list(request.bodies or ["Sun"])

    adapter = SwissEphemerisAdapter.get_default_adapter()
    natal_dt = datetime.fromisoformat(natal.replace("Z", "+00:00")).astimezone(UTC)
    start_dt = datetime.fromisoformat(start.replace("Z", "+00:00")).astimezone(UTC)
    end_dt = datetime.fromisoformat(end.replace("Z", "+00:00")).astimezone(UTC)

    natal_jd = adapter.julian_day(natal_dt)
    start_jd = adapter.julian_day(start_dt)
    end_jd = adapter.julian_day(end_dt)

    hits: list[Hit] = []
    for body in bodies:
        kind = "solar" if body.lower() == "sun" else "lunar"
        kwargs: dict[str, Any] = {"kind": kind}
        if request.step_days is not None:
            kwargs["step_days"] = request.step_days
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

