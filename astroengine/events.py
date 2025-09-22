"""Canonical event dataclasses used by detector modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, MutableMapping

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


@dataclass(slots=True)
class BaseEvent:
    """Common metadata shared by most detector outputs."""

    ts: float
    """Event timestamp expressed as Julian Day (UT)."""

    provenance: str = "swiss_ephemeris"
    """Identifier describing the ephemeris source used to compute the event."""


@dataclass(slots=True)
class LunationEvent(BaseEvent):
    """Represents a lunar phase crossing (new/full/quarters)."""

    kind: str = ""
    """Phase identifier: ``new``, ``full``, ``first_quarter`` or ``third_quarter``."""

    phase_angle: float = 0.0
    """Difference in degrees between Moon and Sun longitudes at the event."""

    sun_longitude: float = 0.0
    moon_longitude: float = 0.0


@dataclass(slots=True)
class EclipseEvent(BaseEvent):
    """Represents a solar or lunar eclipse detected near a lunation."""

    kind: str = ""
    """``solar`` or ``lunar`` depending on the lunation polarity."""

    separation_deg: float = 0.0
    """Absolute lunar latitude at the event (smaller implies stronger eclipse)."""

    phase: str = ""


@dataclass(slots=True)
class StationEvent(BaseEvent):
    """Represents a planetary station when longitudinal speed crosses zero."""

    body: str = ""
    direction: str = ""
    """Direction after the station: ``retrograde`` or ``direct``."""

    longitude: float = 0.0
    speed: float = 0.0


@dataclass(slots=True)
class ReturnEvent(BaseEvent):
    """Represents a solar or lunar return event."""

    body: str = ""
    kind: str = ""
    longitude: float = 0.0


@dataclass(slots=True)
class ProgressionEvent(BaseEvent):
    """Represents a secondary progression snapshot (day-for-a-year)."""

    method: str = "secondary"
    age: float = 0.0
    positions: Mapping[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class DirectionEvent(BaseEvent):
    """Represents a solar arc direction snapshot."""

    method: str = "solar_arc"
    age: float = 0.0
    positions: Mapping[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class ProfectionEvent(BaseEvent):
    """Represents an annual profection change."""

    age: int = 0
    sign_index: int = 0
    ruler: str = ""
    metadata: MutableMapping[str, object] = field(default_factory=dict)

