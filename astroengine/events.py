"""Typed event payloads produced by AstroEngine detectors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

__all__ = [
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
    """Base event with canonical timestamp metadata.

    Attributes
    ----------
    ts:
        ISO-8601 timestamp in UTC.
    jd:
        Julian day (UT) corresponding to ``ts``. Stored as a floating
        point number so downstream consumers can join against Swiss
        Ephemeris data without recomputing it.
    """

    ts: str
    jd: float


@dataclass(frozen=True)
class LunationEvent(BaseEvent):
    """Represents a lunation event (new/full moon).

    sun_longitude and moon_longitude are geocentric ecliptic positions in
    **degrees** normalised to ``[0, 360)``.
    """

    phase: str
    sun_longitude: float
    moon_longitude: float


@dataclass(frozen=True)
class EclipseEvent(BaseEvent):
    """Represents a solar or lunar eclipse.

    Longitudes and latitude are expressed in **degrees**. ``phase``
    distinguishes between partial, annular, total, etc.
    """

    eclipse_type: str
    phase: str
    sun_longitude: float
    moon_longitude: float
    moon_latitude: float


@dataclass(frozen=True)
class StationEvent(BaseEvent):
    """Represents a planetary station (speed crossing zero).

    ``longitude`` is the ecliptic longitude in degrees. ``speed_longitude``
    is measured in degrees per day and hovers near zero at the station
    moment.
    """

    body: str
    motion: str
    longitude: float
    speed_longitude: float


@dataclass(frozen=True)
class ReturnEvent(BaseEvent):
    """Represents a solar or lunar return event.

    ``longitude`` stores the body’s geocentric ecliptic longitude in
    degrees when the return perfects.
    """

    body: str
    method: str
    longitude: float


@dataclass(frozen=True)
class ProgressionEvent(BaseEvent):
    """Represents secondary progression samples.

    ``positions`` maps body names to geocentric ecliptic longitudes in
    degrees. The values are already normalised to ``[0, 360)`` by the
    detectors.
    """

    method: str
    positions: Mapping[str, float]


@dataclass(frozen=True)
class DirectionEvent(BaseEvent):
    """Represents directed positions (e.g., solar arc).

    ``arc_degrees`` is the longitudinal arc applied to each natal body in
    degrees. ``positions`` stores the directed longitudes (degrees).
    """

    method: str
    arc_degrees: float
    positions: Mapping[str, float]


@dataclass(frozen=True)
class ProfectionEvent(BaseEvent):
    """Represents profected year transitions.

    ``house`` is the profected house number (1–12). ``ruler`` references
    the planetary ruler active for the period.
    """

    method: str
    house: int
    ruler: str
