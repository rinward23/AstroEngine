# >>> AUTO-GEN BEGIN: event-types v1.0
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class LunationEvent:
    kind: str  # "new", "first_quarter", "full", "last_quarter"
    ts: str    # ISO-8601 UTC
    lon_moon: float
    lon_sun: float

@dataclass(frozen=True)
class EclipseEvent:
    kind: str  # "solar" or "lunar"
    ts: str
    magnitude: Optional[float] = None

@dataclass(frozen=True)
class StationEvent:
    body: str
    kind: str  # "station_rx" or "station_dx"
    ts: str

@dataclass(frozen=True)
class ReturnEvent:
    body: str  # "Sun" (solar return) or "Moon" (lunar return)
    ts: str

@dataclass(frozen=True)
class ProgressionEvent:
    method: str  # "secondary"
    body: str
    ts: str

@dataclass(frozen=True)
class DirectionEvent:
    method: str  # "solar_arc"
    body: str
    ts: str

@dataclass(frozen=True)
class ProfectionEvent:
    level: int
    start_ts: str
    end_ts: str
# >>> AUTO-GEN END: event-types v1.0
