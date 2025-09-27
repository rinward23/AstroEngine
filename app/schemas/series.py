from __future__ import annotations


from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

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

