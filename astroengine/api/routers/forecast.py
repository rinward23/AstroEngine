from __future__ import annotations

from datetime import UTC, datetime
from io import StringIO
import csv
from typing import Any, Iterable

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel

from ...chart import ChartLocation, compute_natal_chart
from ...chart.natal import expansions_from_groups
from ...config.settings import Settings, load_settings
from ...forecast import ForecastChart, ForecastWindow, build_forecast_stack
from ...userdata.vault import load_natal
from ..errors import ErrorEnvelope

router = APIRouter(prefix="/v1/forecast", tags=["forecast"])


def _coerce_datetime(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


class ForecastEventModel(BaseModel):
    start: datetime
    end: datetime
    body: str
    aspect: str
    target: str
    exactness: float
    technique: str


class ForecastResponse(BaseModel):
    natal_id: str
    start: datetime
    end: datetime
    components: dict[str, bool]
    count: int
    events: list[ForecastEventModel]


def _load_settings() -> Settings:
    return load_settings()


def _csv_response(events: Iterable[dict[str, Any]]) -> Response:
    buffer = StringIO()
    fieldnames = ["start", "end", "body", "aspect", "target", "exactness", "technique"]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for event in events:
        writer.writerow({name: event.get(name, "") for name in fieldnames})
    payload = buffer.getvalue().encode("utf-8")
    return Response(
        content=payload,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=forecast.csv"},
    )


@router.get(
    "",
    response_model=ForecastResponse,
    responses={
        status.HTTP_200_OK: {"description": "Forecast stack."},
        status.HTTP_404_NOT_FOUND: {"model": ErrorEnvelope},
    },
    summary="Compose forecast stack for a natal chart.",
    operation_id="getForecastStack",
)
def get_forecast_stack(
    natal_id: str = Query(..., description="Identifier of the stored natal chart."),
    from_: datetime | str = Query(..., alias="from", description="UTC start timestamp."),
    to: datetime | str = Query(..., description="UTC end timestamp."),
    format: str = Query("json", pattern="^(json|csv)$", description="Response format."),
    techniques: list[str] | None = Query(
        None,
        description="Optional subset of techniques to include (transits, progressions, solar_arc).",
    ),
    settings: Settings = Depends(_load_settings),
) -> ForecastResponse | Response:
    start = _coerce_datetime(from_)
    end = _coerce_datetime(to)
    if end <= start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_WINDOW", "message": "'to' must be after 'from'."},
        )

    try:
        natal = load_natal(natal_id)
    except FileNotFoundError as exc:  # pragma: no cover - depends on filesystem
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NATAL_NOT_FOUND", "message": f"Natal '{natal_id}' was not found."},
        ) from exc

    location = ChartLocation(latitude=float(natal.lat), longitude=float(natal.lon))
    natal_moment = datetime.fromisoformat(natal.utc.replace("Z", "+00:00"))
    if natal_moment.tzinfo is None:
        natal_moment = natal_moment.replace(tzinfo=UTC)
    natal_moment = natal_moment.astimezone(UTC)

    natal_chart = compute_natal_chart(
        natal_moment,
        location,
        config=natal.chart_config(),
    )
    window = ForecastWindow(start=start, end=end)
    chart = ForecastChart(natal_chart=natal_chart, window=window)

    events = build_forecast_stack(settings, chart)

    if techniques:
        allowed = {tech.lower() for tech in techniques}
        events = [event for event in events if event["technique"].lower() in allowed]

    components = dict(getattr(getattr(settings, "forecast_stack", None), "components", {}) or {})
    if not components:
        components = {"transits": True, "progressions": True, "solar_arc": True}
    if format == "csv":
        return _csv_response(events)

    return ForecastResponse(
        natal_id=natal_id,
        start=start,
        end=end,
        components=components,
        count=len(events),
        events=[ForecastEventModel(**event) for event in events],
    )
