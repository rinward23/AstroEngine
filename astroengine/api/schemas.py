"""Pydantic models shared by the public API surface."""

from __future__ import annotations

from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExportSpec(BaseModel):
    """Describe how a scan response should be exported."""

    format: Literal["json", "ics", "parquet", "sqlite"] = "json"
    path: str | None = None
    dataset: str | None = None


class NatalInline(BaseModel):
    """Inline natal data supplied directly to a scan request."""

    ts: str
    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=180.0)

    @field_validator("lat", "lon", mode="before")
    @classmethod
    def _coerce_coordinate(cls, value: Any) -> float:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        if isinstance(value, str):
            candidate = value.strip()
            if not candidate:
                raise ValueError("coordinate must not be empty")
            return float(candidate)
        raise TypeError("coordinate must be numeric or numeric string")


class ScanRequest(BaseModel):
    """Payload accepted by scan endpoints across different modalities."""

    model_config = ConfigDict(populate_by_name=True)

    method: Literal["transits", "progressions", "directions", "returns"]
    natal_inline: NatalInline | None = None
    from_: Annotated[str, Field(alias="from")]
    to: str
    dataset: str | None = None
    bodies: list[str] | None = None
    aspects: list[int] = Field(default_factory=lambda: [0, 60, 90, 120, 180])
    orb_deg: float = 1.5
    step: str = "1d"
    export: ExportSpec | None = None


class Hit(BaseModel):
    """Normalized representation of a detected scan hit."""

    when_iso: str
    moving: str
    target: str
    aspect: int
    orb: float
    applying: bool | None = None
    retrograde: bool | None = None
    speed_deg_per_day: float | None = None


class ScanResponse(BaseModel):
    """Standard response returned by scan endpoints."""

    run_id: UUID = Field(default_factory=uuid4)
    method: Literal["transits", "progressions", "directions", "returns"]
    count: int
    summary: dict[str, int]
    export: ExportSpec | None = None
    hits: list[Hit]
