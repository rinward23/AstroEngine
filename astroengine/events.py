"""Lightweight dataclasses used by detector stubs and tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

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
    ts: float
    kind: str
    metadata: Mapping[str, object] | None = None


@dataclass(frozen=True)
class LunationEvent(BaseEvent):
    phase: str | None = None


@dataclass(frozen=True)
class EclipseEvent(BaseEvent):
    magnitude: float | None = None


@dataclass(frozen=True)
class StationEvent(BaseEvent):
    body: str | None = None
    motion: str | None = None


@dataclass(frozen=True)
class ReturnEvent(BaseEvent):
    body: str | None = None
    cycle: str | None = None


@dataclass(frozen=True)
class ProgressionEvent(BaseEvent):
    method: str | None = None


@dataclass(frozen=True)
class DirectionEvent(BaseEvent):
    method: str | None = None


@dataclass(frozen=True)
class ProfectionEvent(BaseEvent):
    lord: str | None = None
    houses: Sequence[int] | None = None
