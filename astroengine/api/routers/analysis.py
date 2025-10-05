"""FastAPI router exposing Arabic Parts computations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from ...analysis import arabic_parts
from ...analysis.arabic_parts import ArabicPartError
from ...chart.natal import ChartLocation, compute_natal_chart
from ...config import Settings, load_settings
from ...userdata.vault import load_natal

router = APIRouter(prefix="/v1/analysis", tags=["analysis"])


def _parse_utc(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:  # pragma: no cover - defensive
        raise ArabicPartError(f"Invalid ISO timestamp '{value}'") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


class LocationOut(BaseModel):
    latitude: float
    longitude: float


class ArabicPartOut(BaseModel):
    name: str
    longitude: float
    house: int | None = None
    description: str | None = None
    source: str = Field(description="Either 'preset' or 'custom'.")
    day_formula: str
    night_formula: str


class ArabicLotsResponse(BaseModel):
    natal_id: str
    natal_name: str | None = None
    moment: datetime
    location: LocationOut
    is_day: bool
    lots: list[ArabicPartOut]
    metadata: dict[str, Any]

    class Config:
        json_encoders = {datetime: lambda dt: dt.astimezone(UTC).isoformat().replace("+00:00", "Z")}


def _load_settings() -> Settings:
    return load_settings()


@router.get(
    "/lots",
    response_model=ArabicLotsResponse,
    summary="Compute Arabic Parts for a stored natal chart.",
    responses={
        status.HTTP_200_OK: {"description": "Computed Arabic Parts."},
        status.HTTP_404_NOT_FOUND: {"description": "Natal chart not found."},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Unable to evaluate lots."},
    },
)
def compute_arabic_parts(natal_id: str = Query(..., description="Identifier returned from /v1/natals.")) -> ArabicLotsResponse:
    try:
        record = load_natal(natal_id)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NATAL_NOT_FOUND", "message": f"Natal '{natal_id}' was not found."},
        ) from exc

    moment = _parse_utc(record.utc)
    location = ChartLocation(latitude=record.lat, longitude=record.lon)

    try:
        chart = compute_natal_chart(moment, location)
    except Exception as exc:  # pragma: no cover - compute_natal_chart validated elsewhere
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "CHART_COMPUTE_FAILED", "message": str(exc)},
        ) from exc

    settings = _load_settings()
    try:
        result = arabic_parts.compute_all(settings, chart)
    except ArabicPartError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "ARABIC_PART_ERROR", "message": str(exc)},
        ) from exc

    lots_payload = [
        ArabicPartOut(
            name=item.name,
            longitude=item.longitude,
            house=item.house,
            description=item.description,
            source=item.source,
            day_formula=item.day_formula,
            night_formula=item.night_formula,
        )
        for item in result.lots
    ]

    response = ArabicLotsResponse(
        natal_id=natal_id,
        natal_name=getattr(record, "name", None),
        moment=moment,
        location=LocationOut(latitude=record.lat, longitude=record.lon),
        is_day=result.is_day,
        lots=lots_payload,
        metadata=dict(result.metadata),
    )
    return response
