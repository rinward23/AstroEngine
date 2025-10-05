"""Pydantic models for observational geometry endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from ._time import UtcDateTime


class ObserverModel(BaseModel):
    latitude_deg: float = Field(..., ge=-90.0, le=90.0)
    longitude_deg: float = Field(..., ge=-180.0, le=180.0)
    elevation_m: float = Field(default=0.0)


class MetModel(BaseModel):
    temperature_c: float = Field(default=10.0)
    pressure_hpa: float = Field(default=1010.0)


class TopocentricPositionRequest(BaseModel):
    body: int
    moment: UtcDateTime
    observer: ObserverModel
    refraction: bool = True
    met: MetModel | None = None
    horizon_dip_deg: float = 0.0


class TopocentricPositionResponse(BaseModel):
    right_ascension: float
    declination: float
    distance_au: float
    ecliptic_longitude: float
    ecliptic_latitude: float
    altitude: float
    azimuth: float
    refraction_applied: bool


class EventsRequest(BaseModel):
    body: int
    date: UtcDateTime
    observer: ObserverModel
    h0_deg: float = Field(default=-0.5667)
    refraction: bool = True
    met: MetModel | None = None
    horizon_dip_deg: float = 0.0


class EventsResponse(BaseModel):
    rise: datetime | None
    set: datetime | None
    transit: datetime | None


class VisibilityConstraintsModel(BaseModel):
    min_altitude_deg: float = 0.0
    sun_altitude_max_deg: float | None = None
    sun_separation_min_deg: float | None = None
    moon_altitude_max_deg: float | None = None
    refraction: bool = True
    horizon_dip_deg: float = 0.0
    step_seconds: int = 300
    sun_body: int | None = None
    moon_body: int | None = None
    met: MetModel | None = None


class VisibilityRequest(BaseModel):
    body: int
    start: UtcDateTime
    end: UtcDateTime
    observer: ObserverModel
    constraints: VisibilityConstraintsModel


class VisibilityWindowModel(BaseModel):
    start: datetime
    end: datetime
    duration_seconds: float
    max_altitude_deg: float
    max_altitude_time: datetime
    min_sun_separation_deg: float | None = None
    max_sun_separation_deg: float | None = None
    score: float
    details: dict[str, float | None]


class VisibilityResponse(BaseModel):
    windows: list[VisibilityWindowModel]


class HeliacalProfileModel(BaseModel):
    mode: str = "rising"
    min_object_altitude_deg: float = 5.0
    sun_altitude_max_deg: float = -10.0
    sun_separation_min_deg: float = 12.0
    max_airmass: float | None = None
    refraction: bool = True
    search_window_hours: float = 2.0


class HeliacalRequest(BaseModel):
    body: int
    start: UtcDateTime
    end: UtcDateTime
    observer: ObserverModel
    profile: HeliacalProfileModel


class HeliacalResponse(BaseModel):
    instants: list[datetime]


class DiagramRequest(BaseModel):
    body: int
    start: UtcDateTime
    end: UtcDateTime
    observer: ObserverModel
    refraction: bool = True
    met: MetModel | None = None
    horizon_dip_deg: float = 0.0
    step_seconds: int = 300
    include_png: bool = True


class DiagramResponse(BaseModel):
    svg: str
    png_base64: str | None = None
    metadata: dict[str, Any]


__all__ = [
    "DiagramRequest",
    "DiagramResponse",
    "EventsRequest",
    "EventsResponse",
    "HeliacalProfileModel",
    "HeliacalRequest",
    "HeliacalResponse",
    "MetModel",
    "ObserverModel",
    "TopocentricPositionRequest",
    "TopocentricPositionResponse",
    "VisibilityConstraintsModel",
    "VisibilityRequest",
    "VisibilityResponse",
    "VisibilityWindowModel",
]
