from __future__ import annotations

from datetime import date
from typing import List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, conint, constr, model_validator

from .aspects import AspectHit, AspectName, OrbPolicyInline, TimeWindow, StrName


class ScoreSeriesScan(BaseModel):
    objects: List[StrName] = Field(..., description="Objects to include when scanning")
    aspects: List[AspectName] = Field(..., description="Aspect families to score")
    harmonics: List[conint(ge=1, le=64)] = Field(
        default_factory=list,
        description="Optional harmonics to include while scanning",
    )
    window: TimeWindow
    pairs: Optional[List[Tuple[StrName, StrName]]] = Field(
        default=None,
        description="Restrict scan to these pairs when provided",
    )
    orb_policy_id: Optional[int] = Field(default=None)
    orb_policy_inline: Optional[OrbPolicyInline] = Field(default=None)
    step_minutes: int = Field(60, ge=1, le=720, description="Sampling step before refinements")


class ScoreSeriesRequest(BaseModel):
    scan: Optional[ScoreSeriesScan] = Field(
        default=None, description="Scan instructions to produce hits before scoring"
    )
    hits: Optional[List[AspectHit]] = Field(
        default=None, description="Precomputed aspect hits to aggregate"
    )

    @model_validator(mode="after")
    def _exactly_one_mode(self) -> "ScoreSeriesRequest":
        if (self.scan is None) == (self.hits is None):
            raise ValueError("Provide either scan or hits")
        return self

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "Scan window and aggregate",
                    "value": {
                        "scan": {
                            "objects": ["Mars", "Venus"],
                            "aspects": ["sextile"],
                            "window": {
                                "start": "2025-01-01T00:00:00Z",
                                "end": "2025-02-01T00:00:00Z",
                            },
                            "step_minutes": 60,
                            "orb_policy_inline": {"per_aspect": {"sextile": 3.0}},
                        }
                    },
                },
                {
                    "summary": "Aggregate provided hits",
                    "value": {
                        "hits": [
                            {
                                "a": "Mars",
                                "b": "Venus",
                                "aspect": "sextile",
                                "exact_time": "2025-01-15T12:00:00Z",
                                "orb": 0.2,
                                "orb_limit": 3.0,
                                "severity": 0.6,
                            }
                        ]
                    },
                },
            ]
        }
    )


class DailyScore(BaseModel):
    date: date
    score: Optional[float] = Field(default=None, ge=0)


class MonthlyScore(BaseModel):
    month: constr(strip_whitespace=True, min_length=7, max_length=7)
    score: Optional[float] = Field(default=None, ge=0)


class ScoreSeriesMeta(BaseModel):
    count_hits: int = Field(..., ge=0)
    window: Optional[TimeWindow] = None


class ScoreSeriesResponse(BaseModel):
    daily: List[DailyScore] = Field(default_factory=list)
    monthly: List[MonthlyScore] = Field(default_factory=list)
    meta: ScoreSeriesMeta

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "daily": [{"date": "2025-01-15", "score": 0.62}],
                "monthly": [{"month": "2025-01", "score": 0.55}],
                "meta": {
                    "count_hits": 42,
                    "window": {
                        "start": "2025-01-01T00:00:00Z",
                        "end": "2025-02-01T00:00:00Z",
                    },
                },
            }
        }
    )


__all__ = [
    "DailyScore",
    "MonthlyScore",
    "ScoreSeriesMeta",
    "ScoreSeriesRequest",
    "ScoreSeriesResponse",
    "ScoreSeriesScan",
]
