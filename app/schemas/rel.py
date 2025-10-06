from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.aspects import AspectName, OrbPolicyInline


class SynastryRequest(BaseModel):
    pos_a: dict[str, float] = Field(..., description="Chart A longitudes (deg)")
    pos_b: dict[str, float] = Field(..., description="Chart B longitudes (deg)")
    aspects: list[AspectName] = Field(..., description="Aspect names to evaluate")

    orb_policy_id: int | None = None
    orb_policy_inline: OrbPolicyInline | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "pos_a": {"Mars": 10.0, "Sun": 0.0},
                "pos_b": {"Venus": 70.0, "Moon": 180.0},
                "aspects": ["sextile", "trine", "square", "conjunction"],
                "orb_policy_inline": {
                    "per_aspect": {"sextile": 3.0, "square": 6.0}
                },
            }
        }
    )


class SynastryHit(BaseModel):
    a_obj: str
    b_obj: str
    aspect: AspectName
    angle: float
    delta: float
    orb: float
    orb_limit: float


class SynastryGrid(BaseModel):
    counts: dict[str, dict[str, int]]


class SynastryResponse(BaseModel):
    hits: list[SynastryHit]
    grid: SynastryGrid


class CompositeEvent(BaseModel):
    when: datetime
    lat: float
    lon: float


class CompositeMidpointRequest(BaseModel):
    pos_a: dict[str, float]
    pos_b: dict[str, float]
    objects: list[str]
    event_a: CompositeEvent | None = None
    event_b: CompositeEvent | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "pos_a": {"Sun": 10.0, "Moon": 200.0},
                "pos_b": {"Sun": 50.0, "Moon": 220.0},
                "objects": ["Sun", "Moon"],
            }
        }
    )


class CompositeDavisonRequest(BaseModel):
    objects: list[str]
    dt_a: datetime
    dt_b: datetime
    lat_a: float = Field(0.0, description="Latitude of event A in degrees")
    lon_a: float = Field(0.0, description="Longitude of event A in degrees")
    lat_b: float = Field(0.0, description="Latitude of event B in degrees")
    lon_b: float = Field(0.0, description="Longitude of event B in degrees")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "objects": ["Sun", "Venus"],
                "dt_a": "2025-01-01T00:00:00Z",
                "lat_a": 40.7128,
                "lon_a": -74.0060,
                "dt_b": "2025-01-11T00:00:00Z",
                "lat_b": 34.0522,
                "lon_b": -118.2437,
            }
        }
    )


class HouseOutput(BaseModel):
    ascendant: float
    midheaven: float
    cusps: list[float]
    house_system_requested: str
    house_system_used: str
    fallback_reason: str | None = None
    metadata: dict[str, Any] | None = None


class CompositeResponse(BaseModel):
    positions: dict[str, float]
    meta: dict[str, Any] = Field(default_factory=dict)
    houses: HouseOutput | None = None
