"""Pydantic models for the transit ↔ natal overlay API."""
from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field, field_validator

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
    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=180.0)
    alt_m: float | None = Field(default=0.0)

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

    @field_validator("alt_m", mode="before")
    @classmethod
    def _coerce_altitude(cls, value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        if isinstance(value, str):
            candidate = value.strip()
            if not candidate:
                return None
            return float(candidate)
        raise TypeError("altitude must be numeric")

    @field_validator("alt_m")
    @classmethod
    def _validate_altitude(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if not -2000.0 <= value <= 12000.0:
            raise ValueError("altitude must be between -2000 and 12000 meters")
        return value


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

    @field_validator("orbs_deg", "orb_overrides", mode="before")
    @classmethod
    def _normalize_orb_maps(
        cls, value: Dict[str, Any] | None
    ) -> Dict[str, float] | None:
        if value is None:
            return None
        if not isinstance(value, dict):
            raise TypeError("orb overrides must be provided as a mapping")
        normalized: Dict[str, float] = {}
        for key, raw in value.items():
            numeric = float(raw)
            if not 0.0 <= numeric <= 20.0:
                raise ValueError("orb values must be between 0 and 20 degrees")
            normalized[str(key)] = numeric
        return normalized


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
    conj_override: float | None = Field(default=None, ge=0.0, le=20.0)
    opp_override: float | None = Field(default=None, ge=0.0, le=20.0)
    orb_overrides: Dict[str, float] | None = None

    @field_validator("orb_overrides", mode="before")
    @classmethod
    def _validate_orb_overrides(
        cls, value: Dict[str, Any] | None
    ) -> Dict[str, float] | None:
        if value is None:
            return None
        if not isinstance(value, dict):
            raise TypeError("orb_overrides must be a mapping of aspect -> degrees")
        normalized: Dict[str, float] = {}
        for key, raw in value.items():
            numeric = float(raw)
            if not 0.0 <= numeric <= 20.0:
                raise ValueError("orb override values must be between 0 and 20 degrees")
            normalized[str(key)] = numeric
        return normalized


class TransitAspectResponse(BaseModel):
    aspects: list[TransitAspectModel]


class TransitOverlayExportRequest(BaseModel):
    payload: TransitOverlayPositionResponse
    aspects: list[TransitAspectModel] | None = None
    width: int | None = None
    height: int | None = None
    theme: str | None = None
