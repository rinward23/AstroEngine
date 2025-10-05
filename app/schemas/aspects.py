from __future__ import annotations
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple, Any, Literal
from pydantic import BaseModel, Field, ConfigDict, ValidationInfo, constr, conint, field_validator

# ---- Common ---------------------------------------------------------------
StrName = constr(strip_whitespace=True, min_length=1)

class TimeWindow(BaseModel):
    start: datetime = Field(..., description="UTC ISO8601 start time")
    end: datetime = Field(..., description="UTC ISO8601 end time")

    @field_validator("start", "end")
    @classmethod
    def _require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError("window datetimes must be timezone-aware")
        return value

    @field_validator("end")
    @classmethod
    def _end_after_start(cls, v: datetime, info: ValidationInfo) -> datetime:
        s = info.data.get("start")
        if s and v <= s:
            raise ValueError("end must be after start")
        return v

class OrbPolicyInline(BaseModel):
    per_object: Dict[StrName, float] = Field(default_factory=dict)
    per_aspect: Dict[StrName, float] = Field(default_factory=dict)
    adaptive_rules: Dict[str, Any] = Field(default_factory=dict)

# ---- Request --------------------------------------------------------------
AspectName = Literal[
    "conjunction","opposition","square","trine","sextile",
    "quincunx","semisquare","sesquisquare","quintile","biquintile"
]

class AspectSearchRequest(BaseModel):
    objects: List[StrName] = Field(..., description="Objects to include (e.g., Sun, Moon, Mars, Chiron)")
    aspects: List[AspectName] = Field(..., description="Aspect families to scan")
    harmonics: List[conint(ge=1, le=64)] = Field(default_factory=list, description="Harmonics to include (e.g., 5,7,9,13,17)")
    window: TimeWindow

    # If pairs is provided, restrict matches to those exact pairs
    pairs: Optional[List[Tuple[StrName, StrName]]] = Field(default=None)

    orb_policy_id: Optional[int] = Field(default=None)
    orb_policy_inline: Optional[OrbPolicyInline] = Field(default=None)

    step_minutes: int = Field(60, ge=1, le=720, description="Sampling step before root‑finding refinements")

    # Paging and ranking controls
    limit: int = Field(500, ge=1, le=5000)
    offset: int = Field(0, ge=0)
    order_by: Literal["time","severity","orb"] = Field("time")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "objects": ["Sun", "Moon", "Mars", "Venus"],
                "aspects": ["sextile", "trine", "square"],
                "harmonics": [5, 7, 13],
                "window": {"start": "2025-01-01T00:00:00Z", "end": "2025-03-01T00:00:00Z"},
                "pairs": [["Mars", "Venus"]],
                "step_minutes": 60,
                "order_by": "time",
                "limit": 200,
                "orb_policy_inline": {
                    "per_aspect": {"sextile": 3.0, "square": 6.0, "trine": 6.0}
                },
            }
        }
    )

# ---- Response -------------------------------------------------------------
class AspectHit(BaseModel):
    a: StrName
    b: StrName
    aspect: AspectName
    harmonic: Optional[int] = None
    exact_time: datetime
    orb: float = Field(..., ge=0)
    orb_limit: float = Field(..., gt=0)
    severity: Optional[float] = Field(default=None, ge=0)
    meta: Dict[str, Any] = Field(default_factory=dict)

class DayBin(BaseModel):
    date: date
    count: int = Field(..., ge=0)
    score: Optional[float] = Field(default=None, ge=0)

class Paging(BaseModel):
    limit: int
    offset: int
    total: Optional[int] = None

class AspectSearchResponse(BaseModel):
    hits: List[AspectHit]
    bins: List[DayBin] = Field(default_factory=list)
    paging: Paging

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "hits": [
                    {
                        "a": "Mars", "b": "Venus", "aspect": "sextile", "harmonic": 5,
                        "exact_time": "2025-02-14T08:12:00Z", "orb": 0.12, "orb_limit": 3.0,
                        "severity": 0.66
                    }
                ],
                "bins": [
                    {"date": "2025-02-14", "count": 3, "score": 0.71}
                ],
                "paging": {"limit": 200, "offset": 0, "total": 137}
            }
        }
    )
