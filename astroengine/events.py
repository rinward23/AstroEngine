# >>> AUTO-GEN BEGIN: events-dataclasses v1.0
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class LunationEvent:
    kind: str
    ts: str
    sun_lon: Optional[float] = None
    moon_lon: Optional[float] = None
    elongation: Optional[float] = None


@dataclass(frozen=True)
class EclipseEvent:
    kind: str
    ts: str
    magnitude: Optional[float] = None


@dataclass(frozen=True)
class StationEvent:
    body: str
    kind: str
    ts: str
    longitude: Optional[float] = None


@dataclass(frozen=True)
class ReturnEvent:
    kind: str
    body: str
    ts: str
    longitude: Optional[float] = None


@dataclass(frozen=True)
class ProgressionEvent:
    method: str
    body: str
    ts: str
    longitude: Optional[float] = None


@dataclass(frozen=True)
class DirectionEvent:
    method: str
    body: str
    ts: str
    arc: Optional[float] = None
    directed_longitude: Optional[float] = None


__all__ = [
    "LunationEvent",
    "EclipseEvent",
    "StationEvent",
    "ReturnEvent",
    "ProgressionEvent",
    "DirectionEvent",
]
# >>> AUTO-GEN END: events-dataclasses v1.0
