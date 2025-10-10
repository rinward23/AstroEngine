"""Chart-centric API endpoints."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfoNotFoundError

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import or_, select

from app.db.models import Chart, _normalize_tags
from app.db.session import session_scope
from app.repo.charts import ChartRepo
from app.schemas.charts import ChartSummary, ChartTagsUpdate
from astroengine.atlas.tz import LocalTimeResolution, to_utc_with_timezone
from astroengine.chart.natal import ChartLocation, compute_natal_chart
from astroengine.compute import build_payload
from astroengine.config import (
    Settings,
    apply_profile_overlay,
    load_profile_overlay,
)
from astroengine.runtime_config import runtime_settings
from astroengine.report import render_chart_pdf
from astroengine.report.builders import build_chart_report_context

router = APIRouter(prefix="/v1/charts", tags=["charts"])


def _ensure_utc(moment: datetime | None) -> datetime | None:
    if moment is None:
        return None
    if moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


def _apply_profile(settings: Settings, profile_name: str | None) -> tuple[Settings, str]:
    if not profile_name:
        return settings, settings.preset
    try:
        overlay = load_profile_overlay(profile_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Profile '{profile_name}' was not found") from exc
    except Exception as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=400, detail=f"Failed to load profile '{profile_name}'") from exc
    merged = apply_profile_overlay(settings, overlay)
    return merged, profile_name


def _chart_metadata(chart: Chart) -> dict[str, Any]:
    if isinstance(chart.data, Mapping):
        raw = chart.data.get("metadata")
        if isinstance(raw, Mapping):
            return dict(raw)
    return {}


class ChartCreate(BaseModel):
    """Payload for creating a persisted chart."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Display name for the chart subject.")
    kind: str = Field(default="natal", description="Chart classification, e.g. natal or transit.")
    dt_utc: datetime = Field(..., description="Reference datetime in UTC.")
    dt_local: datetime | None = Field(
        default=None,
        description="Original local datetime before timezone normalisation.",
    )
    tz: str = Field(..., description="Original timezone identifier (IANA).")
    tz_fold: int | None = Field(
        default=None,
        ge=0,
        le=1,
        description="PEP 495 fold flag for ambiguous local instants.",
    )
    lat: float = Field(..., description="Latitude in decimal degrees.")
    lon: float = Field(..., description="Longitude in decimal degrees.")
    location: str | None = Field(default=None, description="Human-readable location label.")
    gender: str | None = Field(default=None, description="Optional gender marker.")
    tags: list[str] | str | None = Field(
        default=None,
        description="Tags applied to the chart (string or list).",
    )
    notes: str | None = Field(default=None, description="Free-form notes stored with the chart.")
    profile: str | None = Field(default=None, description="Profile overlay to apply before computation.")
    narrative_profile: str | None = Field(default=None, description="Narrative profile or mix name.")


class ChartUpdate(BaseModel):
    """Metadata updates for an existing chart."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None)
    tags: list[str] | str | None = Field(default=None)
    notes: str | None = Field(default=None)
    gender: str | None = Field(default=None)
    location: str | None = Field(default=None)
    tz: str | None = Field(default=None)
    narrative_profile: str | None = Field(default=None)


class ChartDerive(BaseModel):
    """Input payload when deriving a chart from an existing record."""

    model_config = ConfigDict(extra="forbid")

    kind: str = Field(default="transit", description="Derived chart type, e.g. transit or solar_return.")
    dt_utc: datetime | None = Field(default=None, description="Target datetime for derivation in UTC.")
    profile: str | None = Field(default=None, description="Optional profile override for derivation.")


class ChartImport(BaseModel):
    """Payload used when importing a chart from an export bundle."""

    model_config = ConfigDict(extra="forbid")

    chart: Mapping[str, Any]


class ChartResponse(BaseModel):
    """API representation of a persisted chart."""

    model_config = ConfigDict(extra="forbid")

    id: int
    chart_key: str
    name: str | None
    kind: str | None
    dt_utc: datetime | None
    tz: str | None
    lat: float | None
    lon: float | None
    location: str | None
    gender: str | None
    tags: list[str] = Field(default_factory=list)
    notes: str | None
    profile_applied: str | None
    narrative_profile: str | None
    bodies: dict[str, Any] = Field(default_factory=dict)
    houses: dict[str, Any] = Field(default_factory=dict)
    aspects: list[dict[str, Any]] = Field(default_factory=list)
    patterns: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    settings_snapshot: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


def _chart_to_response(chart: Chart) -> ChartResponse:
    metadata = _chart_metadata(chart)
    return ChartResponse(
        id=chart.id,
        chart_key=str(chart.chart_key),
        name=chart.name,
        kind=str(chart.kind) if chart.kind else None,
        dt_utc=_ensure_utc(chart.dt_utc),
        tz=chart.timezone,
        lat=float(chart.lat) if chart.lat is not None else None,
        lon=float(chart.lon) if chart.lon is not None else None,
        location=chart.location_name,
        gender=chart.gender,
        tags=list(chart.tags or []),
        notes=chart.memo,
        profile_applied=chart.profile_key,
        narrative_profile=chart.narrative_profile,
        bodies=dict(chart.bodies or {}),
        houses=dict(chart.houses or {}),
        aspects=list(chart.aspects or []),
        patterns=list(chart.patterns or []),
        metadata=metadata,
        settings_snapshot=dict(chart.settings_snapshot or {}),
        created_at=_ensure_utc(chart.created_at),
        updated_at=_ensure_utc(chart.updated_at),
        deleted_at=_ensure_utc(getattr(chart, "deleted_at", None)),
    )


def _parse_import_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _ensure_utc(value)
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:  # pragma: no cover - defensive guard
            raise HTTPException(status_code=400, detail=f"Invalid datetime value: {value}") from exc
        return _ensure_utc(dt)
    raise HTTPException(status_code=400, detail="dt_utc must be an ISO timestamp")


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Unable to coerce numeric value: {value}") from exc


def _ensure_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _ensure_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return [dict(item) if isinstance(item, Mapping) else item for item in value]
    if isinstance(value, tuple):
        return [dict(item) if isinstance(item, Mapping) else item for item in value]
    return []


@router.post("", response_model=ChartResponse, status_code=201)
def create_chart(payload: ChartCreate) -> ChartResponse:
    base_settings = runtime_settings.persisted()
    settings, profile_key = _apply_profile(base_settings, payload.profile)
    resolution: LocalTimeResolution | None = None
    if payload.dt_local is not None:
        local_value = payload.dt_local
        if local_value.tzinfo is not None and local_value.tzinfo.utcoffset(local_value) is not None:
            raise HTTPException(status_code=400, detail="dt_local must be timezone-naive")
        local_naive = local_value.replace(tzinfo=None)
        policy = "latest" if payload.tz_fold == 1 else "earliest"
        try:
            resolution = to_utc_with_timezone(local_naive, payload.tz, ambiguous=policy)
        except ZoneInfoNotFoundError as exc:
            raise HTTPException(status_code=400, detail=f"Unrecognised timezone '{payload.tz}'") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        moment = resolution.utc
        expected = _ensure_utc(payload.dt_utc)
        if expected is not None and abs((expected - moment).total_seconds()) > 1e-6:
            raise HTTPException(status_code=400, detail="dt_utc does not match resolved timezone conversion")
    else:
        moment = _ensure_utc(payload.dt_utc)
    if moment is None:
        raise HTTPException(status_code=400, detail="dt_utc is required")
    result = build_payload(moment, float(payload.lat), float(payload.lon), settings)
    metadata = dict(result.get("metadata") or {})
    normalized_tags = _normalize_tags(payload.tags)
    if resolution is not None:
        timezone_meta = resolution.to_metadata()
        timezone_meta["source"] = "local"
    else:
        timezone_meta = {
            "input_local": payload.dt_local.isoformat() if payload.dt_local else None,
            "tzid": payload.tz,
            "resolved_local": None,
            "utc": moment.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "fold": int(payload.tz_fold or 0),
            "ambiguous": None,
            "ambiguous_policy": None,
            "ambiguous_flagged": False,
            "nonexistent": None,
            "nonexistent_policy": None,
            "gap_seconds": None,
            "source": "utc",
        }
    timezone_meta.setdefault("gap_seconds", None)
    metadata["timezone_resolution"] = timezone_meta
    with session_scope() as db:
        chart = Chart(
            name=payload.name,
            kind=payload.kind,
            dt_utc=moment,
            lat=float(payload.lat),
            lon=float(payload.lon),
            timezone=payload.tz,
            location_name=payload.location,
            gender=payload.gender,
            tags=normalized_tags,
            memo=payload.notes,
            profile_key=profile_key,
            narrative_profile=payload.narrative_profile,
            settings_snapshot=settings.model_dump(),
            bodies=result["bodies"],
            houses=result["houses"],
            aspects=result["aspects"],
            patterns=result["patterns"],
            data={"metadata": metadata},
        )
        db.add(chart)
        db.flush()
        db.refresh(chart)
        response = _chart_to_response(chart)
    return response


@router.get("", response_model=list[ChartResponse])
def list_charts(
    kind: str | None = Query(default=None, description="Filter by chart kind."),
    q: str | None = Query(default=None, description="Case-insensitive name search."),
    tags: list[str] | None = Query(
        default=None,
        alias="tag",
        description="Repeatable tag filter (case-insensitive).",
    ),
    limit: int = Query(default=200, ge=1, le=500),
) -> list[ChartResponse]:
    stmt = select(Chart)
    if kind:
        stmt = stmt.where(Chart.kind == kind)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(or_(Chart.name.ilike(pattern), Chart.chart_key.ilike(pattern)))
    stmt = stmt.order_by(Chart.created_at.desc()).limit(limit)
    with session_scope() as db:
        records = db.execute(stmt).scalars().all()
    if tags:
        normalized = _normalize_tags(tags)
        if normalized:
            records = [
                chart
                for chart in records
                if all(tag in (chart.tags or []) for tag in normalized)
            ]
    return [_chart_to_response(chart) for chart in records]


@router.get("/deleted", response_model=list[ChartSummary])
def list_deleted_charts(
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[ChartSummary]:
    repo = ChartRepo()
    with session_scope() as db:
        records = repo.list_deleted(db, limit=limit, offset=offset)
    return [ChartSummary.model_validate(record) for record in records]


@router.get("/{chart_id}", response_model=ChartResponse)
def get_chart(chart_id: int) -> ChartResponse:
    with session_scope() as db:
        chart = db.get(Chart, chart_id)
        if chart is None:
            raise HTTPException(status_code=404, detail="Chart not found")
        return _chart_to_response(chart)


@router.put("/{chart_id}", response_model=ChartResponse)
def update_chart(chart_id: int, payload: ChartUpdate) -> ChartResponse:
    with session_scope() as db:
        chart = db.get(Chart, chart_id)
        if chart is None:
            raise HTTPException(status_code=404, detail="Chart not found")
        updates = payload.model_dump(exclude_unset=True)
        if "notes" in updates:
            chart.memo = updates.pop("notes")
        if "location" in updates:
            chart.location_name = updates.pop("location")
        if "tz" in updates:
            chart.timezone = updates.pop("tz")
        if "narrative_profile" in updates:
            chart.narrative_profile = updates.pop("narrative_profile")
        if "tags" in updates:
            updates["tags"] = _normalize_tags(updates.pop("tags"))
        for field, value in updates.items():
            setattr(chart, field, value)
        db.flush()
        db.refresh(chart)
        return _chart_to_response(chart)


@router.delete("/{chart_id}", status_code=204)
def delete_chart(chart_id: int) -> None:
    repo = ChartRepo()
    with session_scope() as db:
        chart = repo.soft_delete(db, chart_id)
        if chart is None:
            raise HTTPException(status_code=404, detail="Chart not found")


@router.post("/{chart_id}/derive", response_model=ChartResponse)
def derive_chart(chart_id: int, payload: ChartDerive) -> ChartResponse:
    with session_scope() as db:
        base_chart = db.get(Chart, chart_id)
        if base_chart is None:
            raise HTTPException(status_code=404, detail="Chart not found")
        try:
            base_settings = Settings.model_validate(base_chart.settings_snapshot or {})
        except ValidationError:
            base_settings = runtime_settings.persisted()
        settings = base_settings
        profile_key = base_chart.profile_key
        if payload.profile:
            settings, profile_key = _apply_profile(base_settings, payload.profile)
        dt_value = payload.dt_utc or base_chart.dt_utc
        dt_utc = _ensure_utc(dt_value)
        if dt_utc is None:
            raise HTTPException(status_code=400, detail="Derivation requires a datetime")
        if base_chart.lat is None or base_chart.lon is None:
            raise HTTPException(status_code=400, detail="Base chart is missing coordinates")
        result = build_payload(dt_utc, float(base_chart.lat), float(base_chart.lon), settings)
        metadata = dict(result.get("metadata") or {})
        base_metadata = _chart_metadata(base_chart)
        timezone_meta = base_metadata.get("timezone_resolution")
        if timezone_meta and "timezone_resolution" not in metadata:
            metadata["timezone_resolution"] = timezone_meta
        name_prefix = base_chart.name or base_chart.chart_key
        derived_name = f"{name_prefix} — {payload.kind}"
        derived = Chart(
            name=derived_name,
            kind=payload.kind,
            dt_utc=dt_utc,
            lat=base_chart.lat,
            lon=base_chart.lon,
            timezone=base_chart.timezone,
            location_name=base_chart.location_name,
            gender=base_chart.gender,
            tags=base_chart.tags,
            memo=base_chart.memo,
            profile_key=profile_key,
            narrative_profile=base_chart.narrative_profile,
            settings_snapshot=settings.model_dump(),
            bodies=result["bodies"],
            houses=result["houses"],
            aspects=result["aspects"],
            patterns=result["patterns"],
            data={"metadata": metadata, "source_chart_id": chart_id},
        )
        db.add(derived)
        db.flush()
        db.refresh(derived)
        return _chart_to_response(derived)


@router.post("/{chart_id}/restore", response_model=ChartResponse)
def restore_chart(chart_id: int) -> ChartResponse:
    repo = ChartRepo()
    with session_scope() as db:
        chart = repo.restore(db, chart_id)
        if chart is None:
            raise HTTPException(status_code=404, detail="Chart not found")
        db.refresh(chart)
        return _chart_to_response(chart)


@router.get("/{chart_id}/export", response_model=ChartResponse)
def export_chart(chart_id: int) -> ChartResponse:
    with session_scope() as db:
        chart = db.get(Chart, chart_id)
        if chart is None:
            raise HTTPException(status_code=404, detail="Chart not found")
    return _chart_to_response(chart)


@router.patch("/{chart_id}/tags", response_model=ChartResponse)
def update_chart_tags(chart_id: int, payload: ChartTagsUpdate) -> ChartResponse:
    normalized = _normalize_tags(payload.tags)
    with session_scope() as db:
        chart = db.get(Chart, chart_id)
        if chart is None:
            raise HTTPException(status_code=404, detail="Chart not found")
        chart.tags = normalized
        db.flush()
        db.refresh(chart)
        return _chart_to_response(chart)


@router.post("/import", response_model=ChartResponse)
def import_chart(payload: ChartImport) -> ChartResponse:
    data = dict(payload.chart)
    dt_utc = _parse_import_datetime(data.get("dt_utc"))
    chart_key = data.get("chart_key")
    lat = _coerce_float(data.get("lat"))
    lon = _coerce_float(data.get("lon"))
    profile_key = data.get("profile_applied") or data.get("profile_key") or "default"
    bodies = _ensure_mapping(data.get("bodies"))
    houses = _ensure_mapping(data.get("houses"))
    aspects = _ensure_list(data.get("aspects"))
    patterns = _ensure_list(data.get("patterns"))
    settings_snapshot = _ensure_mapping(data.get("settings_snapshot"))
    metadata = _ensure_mapping(data.get("metadata"))
    tags_data = _normalize_tags(data.get("tags"))
    with session_scope() as db:
        existing = None
        if chart_key:
            existing = db.execute(select(Chart).where(Chart.chart_key == str(chart_key))).scalar_one_or_none()
        if existing is None:
            chart = Chart(
                chart_key=str(chart_key) if chart_key is not None else None,
                name=data.get("name"),
                kind=data.get("kind"),
                dt_utc=dt_utc,
                lat=lat,
                lon=lon,
                timezone=data.get("tz") or data.get("timezone"),
                location_name=data.get("location"),
                gender=data.get("gender"),
                tags=tags_data,
                memo=data.get("notes"),
                profile_key=profile_key,
                narrative_profile=data.get("narrative_profile"),
                settings_snapshot=settings_snapshot,
                bodies=bodies,
                houses=houses,
                aspects=aspects,
                patterns=patterns,
                data={"metadata": metadata},
            )
            db.add(chart)
            db.flush()
            db.refresh(chart)
        else:
            existing.name = data.get("name")
            existing.kind = data.get("kind")
            existing.dt_utc = dt_utc
            existing.lat = lat
            existing.lon = lon
            existing.timezone = data.get("tz") or data.get("timezone")
            existing.location_name = data.get("location")
            existing.gender = data.get("gender")
            existing.tags = tags_data
            existing.memo = data.get("notes")
            existing.profile_key = profile_key
            existing.narrative_profile = data.get("narrative_profile")
            existing.settings_snapshot = settings_snapshot
            existing.bodies = bodies
            existing.houses = houses
            existing.aspects = aspects
            existing.patterns = patterns
            existing.data = {"metadata": metadata}
            db.flush()
            db.refresh(existing)
            chart = existing
        return _chart_to_response(chart)


@router.get("/{chart_id}/pdf")
def chart_pdf(chart_id: int) -> Response:
    settings = runtime_settings.persisted()
    if not settings.reports.pdf_enabled:
        raise HTTPException(status_code=403, detail="PDF reports are disabled")

    with session_scope() as db:
        repo = ChartRepo()
        chart = repo.get(db, chart_id, include_deleted=True)
        if chart is None or chart.deleted_at is not None:
            raise HTTPException(status_code=404, detail="Chart not found")
        if chart.dt_utc is None or chart.lat is None or chart.lon is None:
            raise HTTPException(status_code=400, detail="Chart is missing birth data")
        moment = chart.dt_utc
        if moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None:
            moment = moment.replace(tzinfo=UTC)

        location = ChartLocation(latitude=float(chart.lat), longitude=float(chart.lon))
        body_expansions = expansions_from_groups(getattr(settings.bodies, "groups", {}))
        natal = compute_natal_chart(
            moment,
            location,
            body_expansions=body_expansions,
        )

    context = build_chart_report_context(
        chart_id=chart_id,
        natal=natal,
        chart_kind=str(chart.kind) if chart.kind else None,
        profile_key=chart.profile_key,
        chart_timestamp=moment,
        location_name=chart.location_name,
        disclaimers=settings.reports.disclaimers,
        generated_at=datetime.now(UTC),
    )
    pdf_bytes = render_chart_pdf(context)
    headers = {"Content-Disposition": f'attachment; filename="chart_{chart_id}.pdf"'}
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


__all__ = ["router"]

