"""Import/export helpers for charts and configuration."""

from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime
from typing import Iterable, Mapping

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from astroengine.config import Settings, load_settings, save_settings
from app.db.models import Chart
from app.db.session import session_scope
from app.repo.charts import ChartRepo

router = APIRouter(prefix="/v1", tags=["data"])

_VALID_SCOPES = {"charts", "settings"}


def _chart_to_payload(chart: Chart) -> Mapping[str, object | None]:
    return {
        "id": chart.id,
        "name": chart.name,
        "chart_key": chart.chart_key,
        "profile_key": chart.profile_key,
        "kind": chart.kind,
        "dt_utc": chart.dt_utc.isoformat() if chart.dt_utc else None,
        "lat": chart.lat,
        "lon": chart.lon,
        "location_name": chart.location_name,
        "timezone": chart.timezone,
        "source": chart.source,
        "tags": chart.tags,
        "notes": chart.memo,
        "gender": chart.gender,
        "narrative_profile": chart.narrative_profile,
        "settings_snapshot": chart.settings_snapshot,
        "bodies": chart.bodies,
        "houses": chart.houses,
        "aspects": chart.aspects,
        "patterns": chart.patterns,
        "module": chart.module,
        "submodule": chart.submodule,
        "channel": chart.channel,
        "subchannel": chart.subchannel,
        "data": chart.data,
        "tags": chart.tags,
        "deleted_at": chart.deleted_at.isoformat() if chart.deleted_at else None,
    }


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid datetime value: {value}") from exc


def _as_mapping(value: object) -> dict[str, object]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _as_list(value: object) -> list[object]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return []


def _normalize_chart_payload(record: Mapping[str, object]) -> dict[str, object | None]:
    def _as_float(value: object, field: str) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(str(value))
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=f"Invalid {field} value: {value}") from exc

    payload: dict[str, object | None] = {}
    raw_key = record.get("chart_key") or record.get("id")
    payload["chart_key"] = str(raw_key) if raw_key is not None else None
    profile_key = record.get("profile_key", "default")
    payload["profile_key"] = str(profile_key) if profile_key is not None else "default"
    kind = record.get("kind")
    payload["kind"] = str(kind) if kind is not None else None
    payload["name"] = record.get("name")
    payload["tags"] = record.get("tags")
    payload["memo"] = record.get("notes") if record.get("notes") is not None else record.get("memo")
    payload["gender"] = record.get("gender")
    payload["narrative_profile"] = record.get("narrative_profile")
    payload["lat"] = _as_float(record.get("lat"), "lat")
    payload["lon"] = _as_float(record.get("lon"), "lon")
    payload["location_name"] = record.get("location_name")
    payload["timezone"] = record.get("timezone")
    payload["source"] = record.get("source")
    for scope_field in ("module", "submodule", "channel", "subchannel"):
        value = record.get(scope_field)
        payload[scope_field] = str(value) if value is not None else None
    data = record.get("data")
    payload["data"] = _as_mapping(data)
    payload["settings_snapshot"] = _as_mapping(record.get("settings_snapshot"))
    payload["bodies"] = _as_mapping(record.get("bodies"))
    payload["houses"] = _as_mapping(record.get("houses"))
    payload["aspects"] = _as_list(record.get("aspects"))
    payload["patterns"] = _as_list(record.get("patterns"))
    dt_raw = record.get("dt_utc")
    payload["dt_utc"] = _parse_datetime(dt_raw) if isinstance(dt_raw, str) else None
    tags_raw = record.get("tags")
    if isinstance(tags_raw, (list, tuple)):
        payload["tags"] = [
            str(tag).strip().lower()
            for tag in tags_raw
            if isinstance(tag, (str, bytes)) and str(tag).strip()
        ]
    else:
        payload["tags"] = []
    deleted_raw = record.get("deleted_at")
    if isinstance(deleted_raw, str):
        payload["deleted_at"] = _parse_datetime(deleted_raw)
    else:
        payload["deleted_at"] = None
    return payload


@router.get("/export")
def export_data(scope: str = "charts,settings") -> StreamingResponse:
    """Return a ZIP archive containing the requested export scope."""

    requested = {part.strip().lower() for part in scope.split(",") if part.strip()}
    if not requested:
        raise HTTPException(status_code=400, detail="Provide at least one export scope")
    unknown = requested - _VALID_SCOPES
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unsupported export scope: {', '.join(sorted(unknown))}")

    charts_payload: Iterable[Mapping[str, object | None]] = []
    if "charts" in requested:
        with session_scope() as db:
            records = db.execute(select(Chart)).scalars().all()
            charts_payload = [_chart_to_payload(chart) for chart in records]

    settings_payload: dict[str, object] | None = None
    if "settings" in requested:
        settings_payload = load_settings().model_dump()

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        if "charts" in requested:
            archive.writestr("charts.json", json.dumps(list(charts_payload), indent=2, ensure_ascii=False))
        if "settings" in requested and settings_payload is not None:
            archive.writestr("settings.json", json.dumps(settings_payload, indent=2, ensure_ascii=False))

    buffer.seek(0)
    headers = {"Content-Disposition": 'attachment; filename="astroengine_export.zip"'}
    return StreamingResponse(buffer, media_type="application/zip", headers=headers)


@router.post("/import")
async def import_data(bundle: UploadFile = File(...)) -> dict[str, object]:
    """Import charts and settings from a previously exported bundle."""

    contents = await bundle.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file was empty")

    try:
        archive = zipfile.ZipFile(io.BytesIO(contents))
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid ZIP archive") from exc

    charts_processed = 0
    charts_created = 0
    charts_updated = 0
    settings_applied = False

    if "settings.json" in archive.namelist():
        settings_raw = archive.read("settings.json").decode("utf-8")
        settings_data = json.loads(settings_raw)
        settings_model = Settings.model_validate(settings_data)
        save_settings(settings_model)
        settings_applied = True

    if "charts.json" in archive.namelist():
        charts_raw = archive.read("charts.json").decode("utf-8")
        data = json.loads(charts_raw)
        if not isinstance(data, list):
            raise HTTPException(status_code=400, detail="charts.json must contain a list of charts")
        with session_scope() as db:
            repo = ChartRepo()
            for item in data:
                if not isinstance(item, Mapping):
                    continue
                payload = _normalize_chart_payload(item)
                chart_key = payload.get("chart_key")
                if not chart_key:
                    continue
                charts_processed += 1
                existing = db.execute(
                    select(Chart).where(Chart.chart_key == str(chart_key))
                ).scalar_one_or_none()
                create_kwargs = {k: v for k, v in payload.items() if v is not None and k != "id"}
                if existing is None:
                    repo.create(db, **create_kwargs)
                    charts_created += 1
                else:
                    for key, value in create_kwargs.items():
                        setattr(existing, key, value)
                    charts_updated += 1

    archive.close()

    return {
        "charts_processed": charts_processed,
        "charts_created": charts_created,
        "charts_updated": charts_updated,
        "settings_applied": settings_applied,
    }


__all__ = ["router"]
