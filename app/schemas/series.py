from __future__ import annotations


from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.aspects import AspectName, TimeWindow, OrbPolicyInline


class ScanInput(BaseModel):
    objects: List[str]
    aspects: List[AspectName]
    harmonics: List[int] = Field(default_factory=list)
    window: TimeWindow
    step_minutes: int = Field(60, ge=1, le=720)

    orb_policy_id: Optional[int] = None
    orb_policy_inline: Optional[OrbPolicyInline] = None


class HitIn(BaseModel):
    a: str
    b: str
    aspect: AspectName
    exact_time: datetime
    orb: float
    orb_limit: float
    severity: Optional[float] = None


class ScoreSeriesRequest(BaseModel):
    scan: Optional[ScanInput] = None
    hits: Optional[List[HitIn]] = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "Scan inputs with inline policy overrides",
                    "value": {
                        "scan": {
                            "objects": ["Mars", "Venus"],
                            "aspects": ["sextile", "trine"],
                            "harmonics": [5],
                            "window": {
                                "start": "2025-02-01T00:00:00Z",
                                "end": "2025-02-15T00:00:00Z",
                            },
                            "step_minutes": 60,
                            "orb_policy_inline": {
                                "per_aspect": {"sextile": 3.0, "trine": 6.0},
                            },
                        }
                    },
                },
                {
                    "summary": "Precomputed hits for scoring",
                    "value": {
                        "hits": [
                            {
                                "a": "Sun",
                                "b": "Moon",
                                "aspect": "sextile",
                                "exact_time": "2025-02-14T08:12:00Z",
                                "orb": 0.12,
                                "orb_limit": 3.0,
                                "severity": 0.6,
                            }
                        ]
                    },
                },
            ]
        }
    )

    @model_validator(mode="after")
    def _one_of_scan_or_hits(self) -> "ScoreSeriesRequest":
        if (self.scan is None and not self.hits) or (self.scan is not None and self.hits):
            raise ValueError("Provide exactly one of 'scan' or 'hits'")
        return self


class DailyPoint(BaseModel):
    date: date
    score: float


class MonthlyPoint(BaseModel):
    month: str  # YYYY-MM
    score: float


class ScoreSeriesResponse(BaseModel):
    daily: List[DailyPoint]
    monthly: List[MonthlyPoint]
    meta: Dict[str, Any]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "daily": [
                    {"date": "2025-02-14", "score": 0.62},
                    {"date": "2025-02-15", "score": 0.58},
                ],
                "monthly": [
                    {"month": "2025-02", "score": 0.6},
                ],
                "meta": {"source": "plus.transits", "module": "plus"},
            }
        }
    )

