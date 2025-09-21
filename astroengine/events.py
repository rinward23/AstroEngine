"""Lightweight event containers for experimental detectors."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["LunationEvent", "StationEvent", "ReturnEvent"]


@dataclass(slots=True)
class LunationEvent:
    kind: str
    ts: str
    lon_moon: float
    lon_sun: float


@dataclass(slots=True)
class StationEvent:
    body: str
    kind: str
    ts: str


@dataclass(slots=True)
class ReturnEvent:
    body: str
    ts: str
