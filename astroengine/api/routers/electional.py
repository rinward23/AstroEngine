"""Electional constraint search API."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from ...chart.config import ChartConfig
from ...config import load_settings
from ...electional import (
    ElectionalCandidate,
    ElectionalConstraintEvaluation,
    ElectionalSearchParams,
    search_constraints,
)
from .._time import UtcDateTime

router = APIRouter(prefix="/v1/electional", tags=["electional"])


class LocationModel(BaseModel):
    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=180.0)


class ConstraintEvaluationModel(BaseModel):
    constraint: str
    passed: bool
    detail: Dict[str, Any] = Field(default_factory=dict)
    reason: str | None = None


class CandidateModel(BaseModel):
    ts: UtcDateTime
    score: float
    evaluations: List[ConstraintEvaluationModel]


class ElectionalSearchRequest(BaseModel):
    start: UtcDateTime
    end: UtcDateTime
    step_minutes: int = Field(5, ge=1, le=720)
    location: LocationModel
    constraints: List[Dict[str, Any]]
    limit: int | None = Field(default=50, ge=1, le=500)

    @field_validator("constraints")
    @classmethod
    def _validate_constraints(cls, value: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not value:
            raise ValueError("at least one constraint is required")
        return value


class ElectionalSearchResponse(BaseModel):
    count: int
    window: Dict[str, Any]
    candidates: List[CandidateModel]


def _chart_config_from_settings(settings) -> ChartConfig:
    zodiac = getattr(settings.zodiac, "type", "tropical")
    ayanamsha = None
    if zodiac == "sidereal":
        ayanamsha = getattr(settings.zodiac, "ayanamsa", None)
    house_system = getattr(settings.houses, "system", "placidus")
    return ChartConfig(
        zodiac=zodiac,
        ayanamsha=ayanamsha,
        house_system=house_system,
    )


def _convert_candidate(candidate: ElectionalCandidate) -> CandidateModel:
    def _convert_eval(ev: ElectionalConstraintEvaluation) -> ConstraintEvaluationModel:
        detail = dict(ev.detail)
        return ConstraintEvaluationModel(
            constraint=ev.constraint,
            passed=bool(ev.passed),
            detail=detail,
            reason=ev.reason,
        )

    return CandidateModel(
        ts=candidate.ts.astimezone(UTC),
        score=float(candidate.score),
        evaluations=[_convert_eval(ev) for ev in candidate.evaluations],
    )


@router.post("/search", response_model=ElectionalSearchResponse)
def electional_search(request: ElectionalSearchRequest) -> ElectionalSearchResponse:
    settings = load_settings()
    electional_cfg = getattr(settings, "electional", None)
    if electional_cfg is not None and not getattr(electional_cfg, "enabled", True):
        raise HTTPException(status_code=403, detail="Electional search disabled in settings")

    span_days = (request.end - request.start).total_seconds() / 86400.0
    max_days = float(getattr(settings.perf, "max_scan_days", 0))
    if max_days and span_days > max_days + 1e-9:
        raise HTTPException(
            status_code=400,
            detail=f"Scan window of {span_days:.2f} days exceeds cap of {max_days} days",
        )

    chart_config = _chart_config_from_settings(settings)
    params = ElectionalSearchParams(
        start=request.start,
        end=request.end,
        step_minutes=int(request.step_minutes),
        constraints=request.constraints,
        latitude=request.location.lat,
        longitude=request.location.lon,
        limit=request.limit,
    )

    try:
        candidates = search_constraints(params, chart_config=chart_config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    converted = [_convert_candidate(candidate) for candidate in candidates]
    window_meta = {
        "start": request.start.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "end": request.end.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "step_minutes": int(request.step_minutes),
        "span_days": span_days,
    }
    return ElectionalSearchResponse(count=len(converted), window=window_meta, candidates=converted)


__all__ = ["router"]
