"""Endpoints for managing stored natal charts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ...chart.config import ChartConfig
from ...userdata.vault import BASE as NATAL_BASE
from ...userdata.vault import Natal, list_natals, load_natal, save_natal
from ..errors import ErrorEnvelope
from ..pagination import Pagination, get_pagination


router = APIRouter(prefix="/v1/natals", tags=["natals"])


def _coerce_datetime(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    raise TypeError("UTC timestamp must be an ISO-8601 string or datetime instance")


class HouseSettings(BaseModel):
    """Pydantic model encapsulating house system preferences."""

    model_config = ConfigDict(str_strip_whitespace=True)

    system: str = Field(default="placidus", description="Canonical house system name or alias.")

    @field_validator("system", mode="before")
    @classmethod
    def _normalize_system(cls, value: Any) -> str:
        if isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                raise ValueError("house system must not be empty")
            return normalized
        raise TypeError("house system must be a string")


class ZodiacSettings(BaseModel):
    """Pydantic model encapsulating zodiac configuration."""

    model_config = ConfigDict(str_strip_whitespace=True)

    type: str = Field(default="tropical", description="Zodiac type (tropical or sidereal).")
    ayanamsa: str | None = Field(
        default=None,
        description="Sidereal ayanamsa identifier when the zodiac type is sidereal.",
    )

    @field_validator("type", mode="before")
    @classmethod
    def _normalize_type(cls, value: Any) -> str:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if not normalized:
                raise ValueError("zodiac type must not be empty")
            return normalized
        raise TypeError("zodiac type must be a string")

    @field_validator("ayanamsa", mode="before")
    @classmethod
    def _normalize_ayanamsa(cls, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            normalized = value.strip().lower()
            return normalized or None
        raise TypeError("ayanamsa must be a string or null")


class NatalPayload(BaseModel):
    """Incoming payload used to create or update a natal record."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "name": "Apollo 11 Launch",
                    "utc": "1969-07-16T13:32:00Z",
                    "lat": 28.60839,
                    "lon": -80.60433,
                    "tz": "UTC",
                    "place": "Launch Complex 39A, Kennedy Space Center",
                    "houses": {"system": "placidus"},
                    "zodiac": {"type": "tropical"},
                }
            ]
        },
    )

    name: str | None = Field(default=None, description="Display name for the chart owner.")
    utc: datetime = Field(description="Moment of birth in ISO-8601 UTC.")
    lat: float = Field(
        description="Latitude in decimal degrees.", ge=-90.0, le=90.0
    )
    lon: float = Field(
        description="Longitude in decimal degrees.", ge=-180.0, le=180.0
    )
    tz: str | None = Field(default=None, description="Original timezone identifier, if known.")
    place: str | None = Field(default=None, description="Birth location description.")
    houses: "HouseSettings" = Field(
        default_factory=HouseSettings,
        description="House system preferences for derived charts.",
    )
    zodiac: "ZodiacSettings" = Field(
        default_factory=ZodiacSettings,
        description="Zodiac framework applied to derived charts.",
    )

    @field_validator("utc", mode="before")
    @classmethod
    def _validate_utc(cls, value: Any) -> datetime:
        return _coerce_datetime(value)

    @field_validator("lat", "lon", mode="before")
    @classmethod
    def _coerce_coordinate(cls, value: Any) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("coordinate must not be empty")
            return float(value)
        raise TypeError("coordinate must be numeric or numeric string")

    @field_validator("tz", mode="before")
    @classmethod
    def _validate_timezone(cls, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, ZoneInfo):
            return value.key
        tz = str(value).strip()
        if not tz:
            return None
        try:
            ZoneInfo(tz)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"unrecognized timezone '{tz}'") from exc
        return tz

    @field_serializer("utc")
    def _serialize_utc(self, value: datetime) -> str:
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class NatalRecord(NatalPayload):
    """Representation of a stored natal chart."""

    natal_id: str = Field(description="Stable identifier for the natal record.")

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_dataclass(cls, natal_id: str, record: Natal) -> "NatalRecord":
        config = record.chart_config()
        return cls(
            natal_id=natal_id,
            name=record.name,
            utc=_coerce_datetime(record.utc),
            lat=record.lat,
            lon=record.lon,
            tz=record.tz,
            place=record.place,
            houses=HouseSettings(system=config.house_system),
            zodiac=ZodiacSettings(type=config.zodiac, ayanamsa=config.ayanamsha),
        )


class NatalCollection(BaseModel):
    """Paginated collection of natals returned by list endpoints."""

    items: list[NatalRecord]
    total: int
    page: int
    page_size: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "natal_id": "apollo-11-launch",
                        "name": "Apollo 11 Launch",
                        "utc": "1969-07-16T13:32:00Z",
                        "lat": 28.60839,
                        "lon": -80.60433,
                        "tz": "UTC",
                        "place": "Launch Complex 39A, Kennedy Space Center",
                        "houses": {"system": "placidus"},
                        "zodiac": {"type": "tropical"},
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 25,
            }
        }
    )


@router.get(
    "",
    response_model=NatalCollection,
    summary="List stored natal charts.",
    operation_id="listNatals",
    responses={status.HTTP_200_OK: {"description": "Paginated list of natals."}},
)
def list_natals_endpoint(pagination: Pagination = Depends(get_pagination)) -> NatalCollection:
    """Return a paginated view of available natal records."""

    all_ids = list_natals()
    total = len(all_ids)
    start = pagination.offset
    end = start + pagination.limit
    page_ids = all_ids[start:end]
    items = [NatalRecord.from_dataclass(natal_id, load_natal(natal_id)) for natal_id in page_ids]
    return NatalCollection(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get(
    "/{natal_id}",
    response_model=NatalRecord,
    summary="Fetch a single natal chart.",
    operation_id="getNatal",
    responses={
        status.HTTP_200_OK: {"description": "The requested natal chart."},
        status.HTTP_404_NOT_FOUND: {"model": ErrorEnvelope},
    },
)
def get_natal_endpoint(
    natal_id: str = Path(..., description="Identifier returned from the list endpoint."),
) -> NatalRecord:
    try:
        record = load_natal(natal_id)
    except FileNotFoundError as exc:  # pragma: no cover - depends on filesystem state
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "NATAL_NOT_FOUND",
                "message": f"Natal '{natal_id}' was not found.",
            },
        ) from exc
    return NatalRecord.from_dataclass(natal_id, record)


@router.put(
    "/{natal_id}",
    response_model=NatalRecord,
    summary="Create or replace a natal chart.",
    operation_id="upsertNatal",
    responses={
        status.HTTP_200_OK: {"description": "The persisted natal chart."},
        status.HTTP_201_CREATED: {"description": "The persisted natal chart."},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorEnvelope},
    },
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "examples": {
                        "apollo11": {
                            "summary": "Apollo 11 launch data",
                            "value": {
                                "name": "Apollo 11 Launch",
                                "utc": "1969-07-16T13:32:00Z",
                                "lat": 28.60839,
                                "lon": -80.60433,
                                "tz": "UTC",
                                "place": "Launch Complex 39A, Kennedy Space Center",
                                "houses": {"system": "placidus"},
                                "zodiac": {"type": "tropical"},
                            },
                        }
                    }
                }
            }
        }
    },
)
def upsert_natal_endpoint(
    payload: NatalPayload,
    response: Response,
    natal_id: str = Path(..., description="Identifier to assign to the natal chart."),
) -> NatalRecord:
    created = not (NATAL_BASE / f"{natal_id}.json").exists()
    try:
        chart_config = ChartConfig(
            zodiac=payload.zodiac.type,
            ayanamsha=payload.zodiac.ayanamsa,
            house_system=payload.houses.system,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INVALID_CHART_CONFIGURATION",
                "message": str(exc),
            },
        ) from exc
    record = Natal(
        natal_id=natal_id,
        name=payload.name,
        utc=payload.utc.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        lat=float(payload.lat),
        lon=float(payload.lon),
        tz=payload.tz,
        place=payload.place,
        house_system=chart_config.house_system,
        zodiac=chart_config.zodiac,
        ayanamsa=chart_config.ayanamsha,
    )
    save_natal(record)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    # FastAPI ignores return status when not using Response, but we encode creation semantics
    # through the OpenAPI responses table.
    return NatalRecord.from_dataclass(natal_id, record)


__all__ = [
    "router",
    "NatalCollection",
    "NatalPayload",
    "NatalRecord",
]

