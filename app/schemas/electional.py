from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.aspects import OrbPolicyInline, TimeWindow


class AspectRuleIn(BaseModel):
    a: str
    b: str
    aspects: list[str]
    weight: float = 1.0
    orb_override: float | None = None


class ForbiddenRuleIn(BaseModel):
    a: str
    b: str
    aspects: list[str]
    penalty: float = 1.0
    orb_override: float | None = None


class ElectionalSearchRequest(BaseModel):
    window: TimeWindow
    window_minutes: int = Field(..., ge=15, le=60 * 24 * 14, description="Candidate window size in minutes")
    step_minutes: int = Field(60, ge=1, le=720)
    top_k: int = Field(3, ge=1, le=20)

    avoid_voc_moon: bool = False
    allowed_weekdays: list[int] | None = Field(None, description="0=Mon .. 6=Sun")
    allowed_utc_ranges: list[tuple[str, str]] | None = Field(None, description='e.g., [["08:00","22:00"]]')

    orb_policy_id: int | None = None
    orb_policy_inline: OrbPolicyInline | None = None

    required_aspects: list[AspectRuleIn] = Field(default_factory=list)
    forbidden_aspects: list[ForbiddenRuleIn] = Field(default_factory=list)

    class Config:
        schema_extra = {
            "example": {
                "window": {"start": "2025-01-01T00:00:00Z", "end": "2025-03-01T00:00:00Z"},
                "window_minutes": 24 * 60,
                "step_minutes": 60,
                "top_k": 3,
                "avoid_voc_moon": True,
                "allowed_weekdays": [0, 1, 2, 3, 4],
                "allowed_utc_ranges": [["08:00", "22:00"]],
                "orb_policy_inline": {"per_aspect": {"sextile": 3.0, "trine": 6.0, "conjunction": 8.0}},
                "required_aspects": [
                    {"a": "Mars", "b": "Venus", "aspects": ["sextile", "trine"], "weight": 1.0}
                ],
                "forbidden_aspects": [
                    {"a": "Moon", "b": "Saturn", "aspects": ["square", "opposition"], "penalty": 1.0}
                ],
            }
        }


class InstantMatch(BaseModel):
    pair: str
    aspect: str
    orb: float
    limit: float
    score: float | None = None


class InstantViolation(BaseModel):
    pair: str
    aspect: str
    orb: float
    limit: float
    penalty: float | None = None


class InstantOut(BaseModel):
    ts: datetime
    score: float
    reason: str | None = None
    matches: list[InstantMatch] = Field(default_factory=list)
    violations: list[InstantViolation] = Field(default_factory=list)


class WindowOut(BaseModel):
    start: datetime
    end: datetime
    score: float
    samples: int
    avg_score: float
    top_instants: list[InstantOut]
    breakdown: dict[str, Any]


class ElectionalSearchResponse(BaseModel):
    windows: list[WindowOut]
    meta: dict[str, Any] = Field(default_factory=dict)
