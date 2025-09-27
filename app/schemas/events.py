from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.aspects import AspectName, OrbPolicyInline, TimeWindow


class EventIntervalOut(BaseModel):
    kind: Literal["voc_moon", "cazimi", "combust", "under_beams", "return"]
    start: datetime
    end: datetime
    meta: Dict[str, Any] = Field(default_factory=dict)


class VoCMoonRequest(BaseModel):
    window: TimeWindow
    aspects: List[AspectName] = Field(
        ..., description="Aspect set to consider for VoC determination"
    )
    other_objects: List[str] = Field(
        ..., description="Bodies Moon may aspect (e.g., Sun,Mercury,...) not including Moon"
    )
    step_minutes: int = Field(60, ge=1, le=720)

    orb_policy_id: Optional[int] = None
    orb_policy_inline: Optional[OrbPolicyInline] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "window": {
                    "start": "2025-01-01T00:00:00Z",
                    "end": "2025-01-04T00:00:00Z",
                },
                "aspects": [
                    "conjunction",
                    "sextile",
                    "square",
                    "trine",
                    "opposition",
                ],
                "other_objects": [
                    "Sun",
                    "Mercury",
                    "Venus",
                    "Mars",
                    "Jupiter",
                    "Saturn",
                ],
                "step_minutes": 60,
                "orb_policy_inline": {
                    "per_aspect": {
                        "conjunction": 8.0,
                        "sextile": 3.0,
                        "square": 6.0,
                        "trine": 6.0,
                        "opposition": 7.0,
                    }
                },
            }
        }
    )


class CombustCfgIn(BaseModel):
    cazimi_deg: float = 0.2667
    combust_deg: float = 8.0
    under_beams_deg: float = 15.0


class CombustCazimiRequest(BaseModel):
    window: TimeWindow
    planet: str = Field(..., description="Planet to test against Sun")
    step_minutes: int = Field(10, ge=1, le=1440)
    cfg: CombustCfgIn = Field(default_factory=CombustCfgIn)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "window": {
                    "start": "2025-01-01T00:00:00Z",
                    "end": "2025-01-20T00:00:00Z",
                },
                "planet": "Mercury",
                "step_minutes": 10,
                "cfg": {
                    "cazimi_deg": 0.2667,
                    "combust_deg": 8.0,
                    "under_beams_deg": 15.0,
                },
            }
        }
    )


class ReturnsRequest(BaseModel):
    window: TimeWindow
    body: str
    target_lon: float
    step_minutes: int = Field(720, ge=1, le=1440)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "window": {
                    "start": "2025-01-01T00:00:00Z",
                    "end": "2026-02-01T00:00:00Z",
                },
                "body": "Sun",
                "target_lon": 10.0,
                "step_minutes": 720,
            }
        }
    )
