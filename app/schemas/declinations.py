from __future__ import annotations

from typing import Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class DeclinationPosition(BaseModel):
    """Input payload describing a body's ecliptic/declination coordinates."""

    lon: float | None = Field(
        default=None, description="Ecliptic longitude in degrees (optional)."
    )
    declination: float | None = Field(
        default=None, description="Equatorial declination in degrees (optional)."
    )
    lat: float | None = Field(
        default=None, description="Ecliptic latitude in degrees (optional)."
    )

    model_config = ConfigDict(extra="allow")


class DeclinationRequest(BaseModel):
    """Request payload for declination aspect detection."""

    positions: Dict[str, DeclinationPosition] = Field(
        ..., description="Body positions keyed by display name."
    )
    julian_day: float | None = Field(
        default=None,
        description="Julian Day (UT). Optional when declinations are provided directly.",
    )
    zodiac: Literal["tropical", "sidereal"] | None = Field(
        default=None, description="Override zodiac mode (defaults to settings)."
    )
    ayanamsa: Optional[str] = Field(
        default=None,
        description="Sidereal ayanamsa identifier when zodiac='sidereal'.",
    )
    nodes_variant: Literal["mean", "true"] | None = Field(
        default=None, description="Override lunar node variant."
    )
    lilith_variant: Literal["mean", "true"] | None = Field(
        default=None, description="Override Black Moon Lilith variant."
    )
    orb_deg: float | None = Field(
        default=None,
        ge=0.0,
        le=5.0,
        description="Optional orb override in degrees.",
    )


class DeclinationAspectHit(BaseModel):
    """Declination parallel/contraparallel hit description."""

    body_a: str
    body_b: str
    kind: Literal["parallel", "contraparallel"]
    declination_a: float
    declination_b: float
    orb: float = Field(..., ge=0.0)
    delta: float


class DeclinationResponse(BaseModel):
    """Response payload containing declination metadata and aspect hits."""

    declinations: Dict[str, float]
    aspects: list[DeclinationAspectHit]
    orb_deg: float
    enabled: bool


__all__ = [
    "DeclinationAspectHit",
    "DeclinationPosition",
    "DeclinationRequest",
    "DeclinationResponse",
]
