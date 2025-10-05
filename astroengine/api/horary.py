"""FastAPI router for horary chart evaluation."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from pydantic import BaseModel, Field, field_validator

from ..engine.horary import GeoLocation, evaluate_case, get_profile
from ..engine.horary.profiles import HoraryProfile, list_profiles, upsert_profile
from ._time import UtcDateTime

router = APIRouter(prefix="/horary", tags=["horary"])


class LocationModel(BaseModel):
    lat: float = Field(
        ..., description="Latitude in decimal degrees", ge=-90.0, le=90.0
    )
    lon: float = Field(
        ..., description="Longitude in decimal degrees", ge=-180.0, le=180.0
    )
    altitude: float | None = Field(
        None, description="Altitude in meters", ge=-2000.0, le=12000.0
    )

    @field_validator("lat", "lon", mode="before")
    @classmethod
    def _coerce_coordinate(cls, value: Any) -> float:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        if isinstance(value, str):
            candidate = value.strip()
            if not candidate:
                raise ValueError("coordinate must not be empty")
            return float(candidate)
        raise TypeError("coordinate must be numeric or numeric string")

    @field_validator("altitude", mode="before")
    @classmethod
    def _coerce_altitude(cls, value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        if isinstance(value, str):
            candidate = value.strip()
            if not candidate:
                return None
            return float(candidate)
        raise TypeError("altitude must be numeric")

    def to_location(self) -> GeoLocation:
        return GeoLocation(latitude=self.lat, longitude=self.lon, altitude=self.altitude or 0.0)


class HoraryCaseRequest(BaseModel):
    question: str
    asked_at: UtcDateTime
    location: LocationModel
    house_system: str = "placidus"
    quesited_house: int
    profile: str = "Lilly"

    @field_validator("quesited_house")
    @classmethod
    def _house_range(cls, value: int) -> int:
        if not 1 <= int(value) <= 12:
            raise ValueError("quesited_house must be between 1 and 12")
        return value


class ProfilePayload(BaseModel):
    name: str
    orbs: dict[str, Any] | None = None
    dignities: dict[str, float] | None = None
    radicality: dict[str, float] | None = None
    testimony_weights: dict[str, float] | None = None
    classification_thresholds: dict[str, float] | None = None


@router.get("/profiles", response_model=list[HoraryProfile])
def get_profiles() -> list[HoraryProfile]:
    """Return the available horary tradition profiles."""

    return list(list_profiles())


@router.post("/profiles", response_model=HoraryProfile)
def upsert_profile_endpoint(payload: ProfilePayload) -> HoraryProfile:
    """Create or update a horary tradition profile."""

    body = {k: v for k, v in payload.model_dump().items() if v is not None}
    return upsert_profile(body)


@router.post("/case")
def create_case(request: HoraryCaseRequest) -> dict[str, Any]:
    """Evaluate a horary case and return the computed chart and judgement."""

    try:
        get_profile(request.profile)
    except KeyError as exc:  # pragma: no cover - validated by get_profile call
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        result = evaluate_case(
            question=request.question,
            asked_at=request.asked_at,
            location=request.location.to_location(),
            house_system=request.house_system,
            quesited_house=request.quesited_house,
            profile=request.profile,
        )
    except Exception as exc:  # pragma: no cover - surface failure details
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result

__all__ = ["router"]

