"""Dataclasses and schemas for the synastry matrix engine."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, MutableMapping
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from astroengine.core.bodies import canonical_name

from .angles import normalize

__all__ = [
    "EclipticPosition",
    "ChartPositions",
    "Hit",
    "GridCell",
    "OverlayLine",
    "Overlay",
    "Scores",
]


@dataclass(frozen=True)
class EclipticPosition:
    """Minimal ecliptic position description for synastry calculations."""

    longitude: float
    latitude: float = 0.0
    declination: float = 0.0
    speed_longitude: float = 0.0

    def normalized_longitude(self) -> float:
        return normalize(self.longitude)


def _extract_longitude(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, EclipticPosition):
        return float(value.longitude)
    if hasattr(value, "longitude"):
        return float(value.longitude)
    if isinstance(value, Mapping):
        if "longitude" in value:
            return float(value["longitude"])
        if "lon" in value:
            return float(value["lon"])
    raise TypeError(f"Unsupported position payload: {value!r}")


@dataclass(frozen=True)
class ChartPositions:
    """Normalized container for chart body positions."""

    positions: Mapping[str, Any]
    frame: str = "geocentric_ecliptic"
    aliases: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        normalized: MutableMapping[str, float] = {}
        order: list[str] = []
        alias_map = {canonical_name(k): canonical_name(v) for k, v in (self.aliases or {}).items()}
        original_to_canonical: dict[str, str] = {}
        for name, payload in self.positions.items():
            if payload is None:
                continue
            longitude = normalize(_extract_longitude(payload))
            order.append(str(name))
            canonical = canonical_name(name)
            normalized[canonical] = longitude
            original_to_canonical[str(name)] = canonical
        object.__setattr__(self, "_longitudes", dict(normalized))
        object.__setattr__(self, "_order", tuple(order))
        object.__setattr__(self, "_aliases", alias_map)
        object.__setattr__(self, "_original_to_canonical", original_to_canonical)

    @property
    def bodies(self) -> tuple[str, ...]:
        return self._order

    def canonical_bodies(self) -> tuple[str, ...]:
        return tuple(self._longitudes.keys())

    def longitude(self, body: str) -> float | None:
        canonical = canonical_name(body)
        if canonical in self._longitudes:
            return self._longitudes[canonical]
        alias = self._aliases.get(canonical)
        if alias and alias in self._longitudes:
            return self._longitudes[alias]
        return None

    def longitude_map(self) -> Mapping[str, float]:
        return dict(self._longitudes)

    def iter_longitudes(self) -> Iterable[tuple[str, float]]:
        for body in self._order:
            lon = self.longitude(body)
            if lon is not None:
                yield body, lon

    def canonical_name_for(self, body: str) -> str:
        canonical = canonical_name(body)
        if canonical in self._longitudes:
            return canonical
        return self._aliases.get(canonical, canonical)


class Hit(BaseModel):
    """Pydantic representation of an inter-aspect match."""

    model_config = ConfigDict(populate_by_name=True, frozen=True)

    body_a: str = Field(alias="bodyA")
    body_b: str = Field(alias="bodyB")
    aspect: int
    delta: float
    orb: float
    severity: float
    separation: float | None = None


class GridCell(BaseModel):
    """Grid entry containing the best hit for a body pair."""

    model_config = ConfigDict(populate_by_name=True, frozen=True)

    best: Hit | None = None


class OverlayLine(BaseModel):
    """Line segment connecting two bodies for overlay visualization."""

    model_config = ConfigDict(populate_by_name=True, frozen=True)

    body_a: str = Field(alias="bodyA")
    body_b: str = Field(alias="bodyB")
    aspect: int
    severity: float
    offset: float


class Overlay(BaseModel):
    """Overlay payload describing both wheels and connecting aspect lines."""

    model_config = ConfigDict(populate_by_name=True, frozen=True)

    wheel_a: list[tuple[str, float]] = Field(alias="wheelA")
    wheel_b: list[tuple[str, float]] = Field(alias="wheelB")
    lines: list[OverlayLine]


class Scores(BaseModel):
    """Aggregate scoring payload returned by the engine."""

    model_config = ConfigDict(populate_by_name=True, frozen=True)

    by_aspect_family: dict[str, float]
    by_body_family: dict[str, float]
    overall: float
    raw_total: float = Field(alias="rawTotal")
