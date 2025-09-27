from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict

from app.schemas.aspects import AspectName, OrbPolicyInline


class SynastryRequest(BaseModel):
    pos_a: Dict[str, float] = Field(..., description="Chart A longitudes (deg)")
    pos_b: Dict[str, float] = Field(..., description="Chart B longitudes (deg)")
    aspects: List[AspectName] = Field(..., description="Aspect names to evaluate")

    orb_policy_id: Optional[int] = None
    orb_policy_inline: Optional[OrbPolicyInline] = None

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
    counts: Dict[str, Dict[str, int]]


class SynastryResponse(BaseModel):
    hits: List[SynastryHit]
    grid: SynastryGrid


class CompositeMidpointRequest(BaseModel):
    pos_a: Dict[str, float]
    pos_b: Dict[str, float]
    objects: List[str]

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
    objects: List[str]
    dt_a: datetime
    dt_b: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "objects": ["Sun", "Venus"],
                "dt_a": "2025-01-01T00:00:00Z",
                "dt_b": "2025-01-11T00:00:00Z",
            }
        }
    )


class CompositeResponse(BaseModel):
    positions: Dict[str, float]
    meta: Dict[str, Any] = Field(default_factory=dict)
