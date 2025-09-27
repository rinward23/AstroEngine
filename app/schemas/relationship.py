from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from app.schemas.aspects import OrbPolicyInline


# --------------------------- Synastry --------------------------------------
class SynastryRequest(BaseModel):
    posA: Dict[str, float] = Field(..., description="Chart A: body → longitude (deg)")
    posB: Dict[str, float] = Field(..., description="Chart B: body → longitude (deg)")
    aspects: List[str] = Field(
        default_factory=lambda: [
            "conjunction",
            "opposition",
            "square",
            "trine",
            "sextile",
        ]
    )
    orb_policy_inline: Optional[OrbPolicyInline] = None
    per_aspect_weight: Optional[Dict[str, float]] = None
    per_pair_weight: Optional[Dict[Tuple[str, str], float]] = None


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
    hits: List[SynastryHitOut]
    grid: Dict[str, Dict[str, str]]
    overlay: Dict[str, Dict[str, Any]]
    scores: Dict[str, Any]
    meta: Dict[str, Any] = Field(default_factory=dict)


# --------------------------- Composite -------------------------------------
class CompositeRequest(BaseModel):
    posA: Dict[str, float]
    posB: Dict[str, float]
    bodies: Optional[List[str]] = None


class CompositeResponse(BaseModel):
    positions: Dict[str, float]
    meta: Dict[str, Any] = Field(default_factory=dict)


# --------------------------- Davison ---------------------------------------
class GeoIn(BaseModel):
    lat_deg: float
    lon_deg_east: float


class DavisonRequest(BaseModel):
    dtA: datetime
    dtB: datetime
    locA: GeoIn
    locB: GeoIn
    bodies: Optional[List[str]] = None


class DavisonResponse(BaseModel):
    positions: Dict[str, float]
    midpoint_time_utc: datetime
    midpoint_geo: GeoIn
    meta: Dict[str, Any] = Field(default_factory=dict)
