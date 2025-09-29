"""Pydantic schemas for the traditional timing API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

__all__ = [
    "LifeMetadata",
    "LifeRequest",
    "LifeResponse",
    "ProfectionsRequest",
    "ProfectionsResponse",
    "SectRequest",
    "SectResponse",
    "TraditionalChartInput",
    "ZodiacalReleasingRequest",
    "ZodiacalReleasingResponse",
]


class TraditionalChartInput(BaseModel):
    moment: datetime = Field(..., description="Birth moment in ISO-8601")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    house_system: str | None = Field(None, description="Requested house system")


class ProfectionSegmentOut(BaseModel):
    start: datetime
    end: datetime
    house: int
    sign: str
    year_lord: str
    co_rulers: dict[str, Any]
    notes: list[str]


class ProfectionsRequest(BaseModel):
    natal: TraditionalChartInput
    start: datetime
    end: datetime
    mode: Literal["hellenistic", "medieval"] = "hellenistic"


class ProfectionsResponse(BaseModel):
    segments: list[ProfectionSegmentOut]
    meta: dict[str, Any]


class ZodiacalPeriodOut(BaseModel):
    level: int
    start: datetime
    end: datetime
    sign: str
    ruler: str
    lb: bool = False
    lb_from: str | None = None
    lb_to: str | None = None
    metadata: dict[str, Any] | None = None


class ZodiacalReleasingRequest(BaseModel):
    natal: TraditionalChartInput
    lot_sign: str
    start: datetime
    end: datetime
    levels: int = 2
    source: Literal["Spirit", "Fortune"] = "Spirit"
    include_peaks: bool = True


class ZodiacalReleasingResponse(BaseModel):
    levels: dict[str, list[ZodiacalPeriodOut]]
    lot: str
    source: str
    meta: dict[str, Any]


class SectRequest(BaseModel):
    moment: datetime
    latitude: float
    longitude: float


class SectResponse(BaseModel):
    is_day: bool
    luminary_of_sect: str
    malefic_of_sect: str
    benefic_of_sect: str
    sun_altitude_deg: float


class LifeRequest(BaseModel):
    natal: TraditionalChartInput
    include_fortune: bool = False


class LifeMetadata(BaseModel):
    body: str
    degree: float
    sign: str
    house: int
    score: float | None = None
    notes: list[str]
    trace: list[Any]


class AlcocodenOut(BaseModel):
    body: str
    method: str
    indicative_years: dict[str, int] | None = None
    confidence: float
    notes: list[str]
    trace: list[str]


class LifeResponse(BaseModel):
    hyleg: LifeMetadata
    alcocoden: AlcocodenOut
    meta: dict[str, Any]
