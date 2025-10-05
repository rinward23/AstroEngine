"""Pydantic schemas for synastry API endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class NatalInline(BaseModel):
    """Lightweight natal chart descriptor for inline usage."""

    ts: str
    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=180.0)

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


class SynastryRequest(BaseModel):
    """Request payload for synastry aspect computation."""

    subject: NatalInline
    partner: NatalInline
    aspects: list[int] = Field(default_factory=lambda: [0, 60, 90, 120, 180])
    orb_deg: float = Field(2.0, ge=0.0, le=15.0)
    subject_bodies: list[str] | None = None
    partner_bodies: list[str] | None = None


class SynastryHit(BaseModel):
    """Serialized representation of a synastry hit."""

    direction: str
    moving: str
    target: str
    aspect: int
    orb: float
    score: float | None = None
    domains: dict[str, float] | None = None


class SynastryResponse(BaseModel):
    """Synastry aspect response envelope."""

    count: int
    summary: dict[str, int]
    hits: list[SynastryHit]
