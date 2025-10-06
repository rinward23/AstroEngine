from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.aspects import OrbPolicyInline


# --------------------------- Synastry --------------------------------------
class SynastryRequest(BaseModel):
    posA: dict[str, float] = Field(..., description="Chart A: body → longitude (deg)")
    posB: dict[str, float] = Field(..., description="Chart B: body → longitude (deg)")
    aspects: list[str] = Field(
        default_factory=lambda: [
            "conjunction",
            "opposition",
            "square",
            "trine",
            "sextile",
        ]
    )
    orb_policy_inline: OrbPolicyInline | None = None
    per_aspect_weight: dict[str, float] | None = None
    per_pair_weight: dict[tuple[str, str], float] | None = None


class SynastryHitOut(BaseModel):
    a: str
    b: str
    aspect: str
    angle: float
    delta: float
    orb: float
    limit: float
    severity: float


class SynastryResponse(BaseModel):
    hits: list[SynastryHitOut]
    grid: dict[str, dict[str, str]]
    overlay: dict[str, dict[str, Any]]
    scores: dict[str, Any]
    meta: dict[str, Any] = Field(default_factory=dict)


# --------------------------- Composite -------------------------------------
class CompositeEventIn(BaseModel):
    when: datetime
    lat_deg: float
    lon_deg_east: float


class CompositeRequest(BaseModel):
    posA: dict[str, float]
    posB: dict[str, float]
    bodies: list[str] | None = None
    eventA: CompositeEventIn | None = None
    eventB: CompositeEventIn | None = None


class HouseOut(BaseModel):
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
    houses: HouseOut | None = None


# --------------------------- Davison ---------------------------------------
class GeoIn(BaseModel):
    lat_deg: float
    lon_deg_east: float


class DavisonRequest(BaseModel):
    dtA: datetime
    dtB: datetime
    locA: GeoIn
    locB: GeoIn
    bodies: list[str] | None = None


class DavisonResponse(BaseModel):
    positions: dict[str, float]
    midpoint_time_utc: datetime
    midpoint_geo: GeoIn
    meta: dict[str, Any] = Field(default_factory=dict)
    houses: HouseOut | None = None
