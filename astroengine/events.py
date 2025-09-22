"""Structured event records produced by AstroEngine detectors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

__all__ = [
    "BaseEvent",
    "LunationEvent",
    "EclipseEvent",
    "StationEvent",
    "ReturnEvent",
    "ProgressionEvent",
    "DirectionEvent",
    "ProfectionEvent",
]


@dataclass(frozen=True)
class BaseEvent:
    """Common event fields shared by all detector outputs."""

    ts: str
    jd: float

    def _base_dict(self) -> dict[str, Any]:
        return {"timestamp": self.ts, "julian_day": float(self.jd)}


@dataclass(frozen=True)
class LunationEvent(BaseEvent):
    """Represents a lunation (new/full/quarter moon) occurrence."""

    phase: str
    phase_deg: float
    sun_longitude: float
    moon_longitude: float

    def to_dict(self) -> dict[str, Any]:
        payload = self._base_dict()
        payload.update(
            {
                "kind": "lunation",
                "phase": self.phase,
                "phase_deg": float(self.phase_deg),
                "sun_longitude": float(self.sun_longitude),
                "moon_longitude": float(self.moon_longitude),
            }
        )
        return payload


@dataclass(frozen=True)
class EclipseEvent(BaseEvent):
    """Represents a solar or lunar eclipse tied to a lunation."""

    eclipse_type: str
    phase: str
    sun_longitude: float
    moon_longitude: float
    moon_latitude: float

    def to_dict(self) -> dict[str, Any]:
        payload = self._base_dict()
        payload.update(
            {
                "kind": f"{self.eclipse_type}_eclipse",
                "phase": self.phase,
                "sun_longitude": float(self.sun_longitude),
                "moon_longitude": float(self.moon_longitude),
                "moon_latitude": float(self.moon_latitude),
            }
        )
        return payload


@dataclass(frozen=True)
class StationEvent(BaseEvent):
    """Represents a planetary station (retrograde or direct)."""

    body: str
    motion: str
    longitude: float
    speed_before: float
    speed_after: float

    def to_dict(self) -> dict[str, Any]:
        payload = self._base_dict()
        payload.update(
            {
                "kind": "station",
                "body": self.body,
                "motion": self.motion,
                "longitude": float(self.longitude),
                "speed_before": float(self.speed_before),
                "speed_after": float(self.speed_after),
            }
        )
        return payload


@dataclass(frozen=True)
class ReturnEvent(BaseEvent):
    """Represents a solar or lunar return."""

    body: str
    method: str
    longitude: float
    location: Mapping[str, float] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = self._base_dict()
        payload.update(
            {
                "kind": "return",
                "body": self.body,
                "method": self.method,
                "longitude": float(self.longitude),
            }
        )
        if self.location:
            payload["location"] = dict(self.location)
        return payload


@dataclass(frozen=True)
class ProgressionEvent(BaseEvent):
    """Represents a progressed chart snapshot for a given epoch."""

    method: str
    progressed_jd: float
    positions: Mapping[str, float]

    def to_dict(self) -> dict[str, Any]:
        payload = self._base_dict()
        payload.update(
            {
                "kind": "progression",
                "method": self.method,
                "progressed_jd": float(self.progressed_jd),
                "positions": {k: float(v) for k, v in self.positions.items()},
            }
        )
        return payload


@dataclass(frozen=True)
class DirectionEvent(BaseEvent):
    """Represents a directed chart snapshot (e.g., solar arc)."""

    method: str
    arc_degrees: float
    positions: Mapping[str, float]

    def to_dict(self) -> dict[str, Any]:
        payload = self._base_dict()
        payload.update(
            {
                "kind": "direction",
                "method": self.method,
                "arc_degrees": float(self.arc_degrees),
                "positions": {k: float(v) for k, v in self.positions.items()},
            }
        )
        return payload


@dataclass(frozen=True)
class ProfectionEvent(BaseEvent):
    """Placeholder for annual profection events (future expansion)."""

    method: str = field(default="annual")
    house: int | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = self._base_dict()
        payload.update({"kind": "profection", "method": self.method})
        if self.house is not None:
            payload["house"] = int(self.house)
        return payload
