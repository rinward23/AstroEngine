"""Pydantic models for the transit ↔ natal overlay API."""
from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field

from ._time import UtcDateTime

__all__ = [
    "GeoPointModel",
    "TransitOverlayOptionsModel",
    "TransitOverlayPositionRequest",
    "OverlayBodyPositionModel",
    "OverlayFrameModel",
    "TransitOverlayPositionResponse",
    "TransitAspectModel",
    "TransitAspectRequest",
    "TransitAspectResponse",
    "TransitOverlayExportRequest",
]


class GeoPointModel(BaseModel):
    lat: float
    lon: float
    alt_m: float | None = 0.0


class TransitOverlayOptionsModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    eph_source: str | None = None
    zodiac: str | None = None
    ayanamsha: str | None = None
    house_system: str | None = None
    nodes_variant: str | None = None
    lilith_variant: str | None = None
    orbs_deg: Dict[str, float] | None = None
    orb_overrides: Dict[str, float] | None = None


class TransitOverlayPositionRequest(BaseModel):
    birth_dt_utc: UtcDateTime
    birth_location: GeoPointModel
    transit_dt_utc: UtcDateTime
    bodies: list[str]
    options: TransitOverlayOptionsModel | None = None


class OverlayBodyPositionModel(BaseModel):
    id: str
    lon_deg: float
    lat_deg: float
    radius_au: float
    speed_lon_deg_per_day: float
    speed_lat_deg_per_day: float
    speed_radius_au_per_day: float
    retrograde: bool
    frame: str
    metadata: Dict[str, Any] | None = None


class OverlayFrameModel(BaseModel):
    timestamp: UtcDateTime
    heliocentric: Dict[str, OverlayBodyPositionModel]
    geocentric: Dict[str, OverlayBodyPositionModel]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TransitOverlayPositionResponse(BaseModel):
    natal: OverlayFrameModel
    transit: OverlayFrameModel
    options: Dict[str, Any] = Field(default_factory=dict)


class TransitAspectModel(BaseModel):
    body: str
    kind: str
    separation_deg: float
    orb_abs_deg: float


class TransitAspectRequest(BaseModel):
    natal: OverlayFrameModel
    transit: OverlayFrameModel
    conj_override: float | None = None
    opp_override: float | None = None
    orb_overrides: Dict[str, float] | None = None


class TransitAspectResponse(BaseModel):
    aspects: list[TransitAspectModel]


class TransitOverlayExportRequest(BaseModel):
    payload: TransitOverlayPositionResponse
    aspects: list[TransitAspectModel] | None = None
    width: int | None = None
    height: int | None = None
    theme: str | None = None
