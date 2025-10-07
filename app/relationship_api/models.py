"""Pydantic models for the relationship API."""

from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, RootModel

Body = Literal[
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
    "Chiron",
    "Node",
]

Aspect = Literal[0, 30, 45, 60, 72, 90, 120, 135, 144, 150, 180]


class EclipticPos(BaseModel):
    lon: float = Field(ge=0.0, lt=360.0, description="Ecliptic longitude in degrees")
    lat: float | None = Field(default=None, description="Ecliptic latitude in degrees")
    dist: float | None = Field(default=None, description="Optional distance in AU")

    model_config = ConfigDict(extra="forbid")


class ChartPositions(RootModel[dict[Body, EclipticPos]]):
    pass


class BirthEvent(BaseModel):
    when: AwareDatetime
    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "when": "1985-01-17T12:15:00Z",
            "lat": 40.7128,
            "lon": -74.0060,
        }
    })


class OrbPolicy(BaseModel):
    base_orb_by_body: dict[str, float] = Field(default_factory=dict)
    cap_by_aspect: dict[int, float] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class Weights(BaseModel):
    aspect_family: dict[str, float] = Field(default_factory=dict)
    body_family: dict[str, float] = Field(default_factory=dict)
    conjunction_sign: float = 1.0

    model_config = ConfigDict(extra="forbid")


class SynastryRequest(BaseModel):
    positionsA: ChartPositions
    positionsB: ChartPositions
    aspects: tuple[Aspect, ...] | None = None
    orb_policy: OrbPolicy | None = None
    weights: Weights | None = None
    gamma: float = Field(default=1.0, ge=0.1, le=4.0)
    min_severity: float = Field(default=0.0, ge=0.0)
    top_k: int | None = Field(default=None, ge=1)
    offset: int = Field(default=0, ge=0)
    limit: int | None = Field(default=None, ge=1)

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "positionsA": {
                "Sun": {"lon": 10.0, "lat": 0.0},
                "Moon": {"lon": 120.5},
            },
            "positionsB": {
                "Sun": {"lon": 190.0},
                "Moon": {"lon": 300.0},
            },
            "min_severity": 0.25,
            "top_k": 5,
        }
    })


class Hit(BaseModel):
    bodyA: Body
    bodyB: Body
    aspect: Aspect
    delta: float
    orb: float
    severity: float

    model_config = ConfigDict(extra="forbid")


class GridCell(BaseModel):
    best: Hit | None = None

    model_config = ConfigDict(extra="forbid")


class Overlay(BaseModel):
    wheelA: list[tuple[Body, float]]
    wheelB: list[tuple[Body, float]]
    lines: list[dict]

    model_config = ConfigDict(extra="forbid")


class Scores(BaseModel):
    by_aspect_family: dict[str, float]
    by_body_family: dict[str, float]
    overall: float

    model_config = ConfigDict(extra="forbid")


class SynastryResponse(BaseModel):
    hits: list[Hit]
    grid: dict[str, dict[str, GridCell]]
    overlay: Overlay
    scores: Scores

    model_config = ConfigDict(extra="forbid")


class CompositeRequest(BaseModel):
    positionsA: ChartPositions
    positionsB: ChartPositions
    bodies: list[Body] | None = None

    model_config = ConfigDict(extra="forbid", json_schema_extra={
        "example": {
            "positionsA": {"Sun": {"lon": 10.0}},
            "positionsB": {"Sun": {"lon": 20.0}},
        }
    })


class CompositeResponse(BaseModel):
    positions: ChartPositions

    model_config = ConfigDict(extra="forbid")


class DavisonRequest(BaseModel):
    birthA: BirthEvent
    birthB: BirthEvent
    bodies: list[Body]
    node_policy: Literal["true", "mean"] = "true"
    eph: Literal["swiss", "skyfield"] = "swiss"

    model_config = ConfigDict(extra="forbid", json_schema_extra={
        "example": {
            "birthA": {"when": "1985-01-17T12:15:00Z", "lat": 40.7128, "lon": -74.0060},
            "birthB": {"when": "1990-11-30T09:30:00Z", "lat": 51.5072, "lon": -0.1276},
            "bodies": ["Sun", "Moon", "Venus"],
        }
    })


class DavisonResponse(BaseModel):
    mid_when: AwareDatetime
    mid_lat: float
    mid_lon: float
    positions: ChartPositions

    model_config = ConfigDict(extra="forbid")


class ApiError(BaseModel):
    code: str
    message: str
    details: dict[str, object] | None = None

    model_config = ConfigDict(extra="forbid")


__all__ = [
    "ApiError",
    "Aspect",
    "BirthEvent",
    "Body",
    "ChartPositions",
    "CompositeRequest",
    "CompositeResponse",
    "DavisonRequest",
    "DavisonResponse",
    "EclipticPos",
    "GridCell",
    "Hit",
    "Overlay",
    "OrbPolicy",
    "Scores",
    "SynastryRequest",
    "SynastryResponse",
    "Weights",
]
