"""Pydantic schemas for synastry API endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class NatalInline(BaseModel):
    """Lightweight natal chart descriptor for inline usage."""

    ts: str
    lat: float
    lon: float


class SynastryRequest(BaseModel):
    """Request payload for synastry aspect computation."""

    a: NatalInline
    b: NatalInline
    aspects: list[int] = Field(default_factory=lambda: [0, 60, 90, 120, 180])
    orb_deg: float = 2.0
    bodies_a: list[str] | None = None
    bodies_b: list[str] | None = None


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
