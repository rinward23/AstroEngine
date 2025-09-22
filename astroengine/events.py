"""Typed event payloads produced by AstroEngine detectors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

__all__ = [
    "LunationEvent",
    "EclipseEvent",
    "StationEvent",
    "IngressEvent",
    "ReturnEvent",
    "ProgressionEvent",
    "DirectionEvent",
    "ProfectionEvent",

    "DashaPeriod",

    "IngressEvent",
    "OutOfBoundsEvent",
    "DashaPeriodEvent",
    "ZodiacalReleasingPeriod",



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
    is_visible: bool | None = None


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
class IngressEvent(BaseEvent):
    """Represents a zodiacal ingress for a moving body."""

    body: str
    sign_from: str
    sign_to: str
    longitude: float
    speed_longitude: float
    retrograde: bool


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
class DashaPeriod(BaseEvent):
    """Represents a Vimsottari dasha sub-period covering ``ts`` → ``end_ts``."""

    method: str
    major_lord: str
    sub_lord: str
    end_jd: float
    end_ts: str


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

    end_ts: str
    midpoint_ts: str



@dataclass(frozen=True)

class IngressEvent(BaseEvent):
    """Represents a zodiac sign ingress for a given body."""

    body: str
    from_sign: str
    to_sign: str
    longitude: float
    motion: str
    speed_deg_per_day: float


class OutOfBoundsEvent(BaseEvent):
    """Represents a declination out-of-bounds crossing for a body."""

    body: str
    state: str  # "enter" or "exit"
    hemisphere: str  # "north" or "south"
    declination: float
    limit: float


@dataclass(frozen=True)
class TimelordPeriod(BaseEvent):
    """Base container for timelord periods with start/end metadata."""

    method: str
    level: str
    ruler: str
    end_ts: str
    end_jd: float


@dataclass(frozen=True)
class DashaPeriodEvent(TimelordPeriod):
    """Represents a Vimshottari dasha or sub-period."""

    parent: str | None = None


@dataclass(frozen=True)
class ZodiacalReleasingPeriod(TimelordPeriod):
    """Represents a zodiacal releasing period for a given lot."""

    lot: str
    sign: str


