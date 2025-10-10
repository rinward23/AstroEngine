"""Return and ingress endpoints for the public API."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ...analysis import aries_ingress_year, lunar_return_datetimes, solar_return_datetime
from ...analysis.returns import ReturnComputationError
from ...runtime_config import runtime_settings
from ...userdata.vault import Natal, load_natal

router = APIRouter(prefix="/v1", tags=["returns"])


class ReturnsResponse(BaseModel):
    """Datetimes for return charts and Aries ingress events."""

    timezone: str | None = Field(
        default=None,
        description="Timezone used to express the returned timestamps.",
    )
    solar: datetime | None = Field(
        default=None,
        description="Solar return timestamp when requested and enabled.",
    )
    lunar: list[datetime] | None = Field(
        default=None,
        description="Sequence of lunar return timestamps when requested.",
    )
    aries_ingress: datetime | None = Field(
        default=None,
        description="Timestamp of the Aries ingress when requested.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "timezone": "America/New_York",
                "solar": "2024-05-04T08:21:15-04:00",
                "lunar": [
                    "2024-05-31T12:11:02-04:00",
                    "2024-06-27T16:03:55-04:00",
                ],
                "aries_ingress": "2024-03-19T23:06:21-04:00",
            }
        }
    }


_TYPE_ALIASES = {
    "solar": "solar",
    "solar_return": "solar",
    "sun": "solar",
    "lunar": "lunar",
    "lunar_return": "lunar",
    "moon": "lunar",
    "aries": "aries_ingress",
    "aries_ingress": "aries_ingress",
    "ingress": "aries_ingress",
}


def _normalize_types(raw: str | None, enabled: dict[str, bool]) -> list[str]:
    if raw:
        requested: list[str] = []
        for chunk in raw.split(","):
            token = chunk.strip().lower()
            if not token:
                continue
            try:
                canonical = _TYPE_ALIASES[token]
            except KeyError:
                raise HTTPException(status_code=400, detail=f"Unknown return type '{token}'")
            if canonical not in requested:
                requested.append(canonical)
        if not requested:
            raise HTTPException(status_code=400, detail="No valid return types requested")
    else:
        requested = [name for name, flag in enabled.items() if flag]

    missing = [name for name in requested if not enabled.get(name, False)]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Requested types disabled by configuration: {', '.join(sorted(missing))}",
        )
    return requested


def _parse_natal(natal: Natal) -> tuple[datetime, str | None]:
    moment = datetime.fromisoformat(natal.utc.replace("Z", "+00:00"))
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    else:
        moment = moment.astimezone(UTC)
    return moment, natal.tz


def _resolve_timezone(preferred: str | None, fallback: str | None) -> str | None:
    tz = (preferred or "").strip() or (fallback or "").strip()
    return tz or None


@router.get(
    "/returns",
    response_model=ReturnsResponse,
    summary="Solar and lunar return timestamps plus Aries ingress",
)
def get_returns(
    natal_id: str = Query(..., description="Identifier for the stored natal chart."),
    year: int = Query(..., ge=1, description="Calendar year anchoring the return."),
    types: str | None = Query(
        None,
        description="Comma separated list of return types (solar,lunar,aries_ingress).",
    ),
) -> ReturnsResponse:
    try:
        natal = load_natal(natal_id)
    except FileNotFoundError as exc:  # pragma: no cover - filesystem dependent
        raise HTTPException(status_code=404, detail=f"Natal '{natal_id}' not found") from exc

    settings = runtime_settings.persisted()
    cfg = settings.returns_ingress
    enabled = {
        "solar": cfg.solar_return,
        "lunar": cfg.lunar_return,
        "aries_ingress": cfg.aries_ingress,
    }

    requested = _normalize_types(types, enabled)
    natal_dt, natal_tz = _parse_natal(natal)
    tz_name = _resolve_timezone(cfg.timezone, natal_tz)

    response = ReturnsResponse(timezone=tz_name)

    if "solar" in requested:
        try:
            response.solar = solar_return_datetime(natal_dt, tz_name, year)
        except ReturnComputationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    if "lunar" in requested:
        try:
            response.lunar = lunar_return_datetimes(
                natal_dt,
                n=cfg.lunar_count,
                tz=tz_name,
            )
        except ReturnComputationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    if "aries_ingress" in requested:
        try:
            response.aries_ingress = aries_ingress_year(year, tz=tz_name)
        except ReturnComputationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    return response


__all__ = ["router"]
