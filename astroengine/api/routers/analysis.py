"""API endpoints exposing dignity analysis reports."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from ...analysis import condition_report
from ...chart.natal import ChartLocation, compute_natal_chart
from ...config import load_settings
from ...userdata import load_natal

router = APIRouter(prefix="/v1/analysis", tags=["analysis"])


def _parse_moment(value: str) -> datetime:
    raw = value.strip()
    if not raw:
        raise ValueError("Natal record missing UTC timestamp")
    normalized = raw.replace("Z", "+00:00")
    moment = datetime.fromisoformat(normalized)
    if moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment


@router.get("/dignities")
def dignities_report(natal_id: str = Query(..., description="Identifier of the stored natal chart")) -> dict[str, object]:
    settings = load_settings()
    cfg = getattr(settings, "dignities", None)
    if not cfg or not cfg.enabled:
        raise HTTPException(status_code=404, detail="Dignities analysis is disabled in server settings")
    if cfg.scoring != "lilly":
        raise HTTPException(status_code=400, detail=f"Unsupported dignities scoring mode '{cfg.scoring}'")

    try:
        entry = load_natal(natal_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Natal '{natal_id}' was not found") from exc

    try:
        moment = _parse_moment(entry.utc)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    location = ChartLocation(latitude=float(entry.lat), longitude=float(entry.lon))
    chart = compute_natal_chart(moment, location)

    try:
        report = condition_report(chart)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    report["natal"] = {
        "natal_id": entry.natal_id,
        "name": entry.name,
        "utc": entry.utc,
        "latitude": entry.lat,
        "longitude": entry.lon,
        "tz": entry.tz,
        "place": entry.place,
    }
    return report
