"""Typed event payloads produced by AstroEngine detectors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

__all__ = [
    "BaseEvent",
    "LunationEvent",
    "EclipseEvent",
    "StationEvent",
    "IngressEvent",
    "ReturnEvent",
    "DashaPeriod",
    "ProgressionEvent",
    "DirectionEvent",
    "ProfectionEvent",
    "OutOfBoundsEvent",
    "TimelordPeriod",
    "DashaPeriodEvent",
    "ZodiacalReleasingPeriod",
]


@dataclass(frozen=True)
class BaseEvent:
    """Base event with canonical timestamp metadata."""

    ts: str
    jd: float


@dataclass(frozen=True)
class LunationEvent(BaseEvent):
    """Represents a lunation event (new/full moon)."""

    phase: str
    sun_longitude: float
    moon_longitude: float


@dataclass(frozen=True)
class EclipseEvent(BaseEvent):
    """Represents a solar or lunar eclipse."""

    eclipse_type: str
    phase: str
    sun_longitude: float
    moon_longitude: float
    moon_latitude: float
    is_visible: bool | None = None


@dataclass(frozen=True)
class StationEvent(BaseEvent):
    """Represents a planetary station (speed crossing zero)."""

    body: str
    motion: str
    longitude: float
    speed_longitude: float


@dataclass(frozen=True)
class IngressEvent(BaseEvent):
    """Represents a zodiacal ingress for a moving body."""

    body: str
    from_sign: str
    to_sign: str
    longitude: float
    motion: str
    speed_deg_per_day: float
    sign_index: int | None = None

    @property
    def sign(self) -> str:
        """Alias returning :pyattr:`to_sign` for legacy callers."""

        return self.to_sign

    @property
    def sign_from(self) -> str:
        return self.from_sign

    @property
    def sign_to(self) -> str:
        return self.to_sign

    @property
    def retrograde(self) -> bool:
        return self.motion.lower() == "retrograde"

    @property
    def speed_longitude(self) -> float:
        return self.speed_deg_per_day


@dataclass(frozen=True)
class ReturnEvent(BaseEvent):
    """Represents a solar or lunar return event."""

    body: str
    method: str
    longitude: float


@dataclass(frozen=True)
class DashaPeriod(BaseEvent):
    """Represents a Vimśottarī daśā sub-period covering ``ts`` → ``end_ts``."""

    method: str
    major_lord: str
    sub_lord: str
    end_jd: float
    end_ts: str


@dataclass(frozen=True)
class ProgressionEvent(BaseEvent):
    """Represents secondary progression samples."""

    method: str
    positions: Mapping[str, float]


@dataclass(frozen=True)
class DirectionEvent(BaseEvent):
    """Represents directed positions (e.g., solar arc)."""

    method: str
    arc_degrees: float
    positions: Mapping[str, float]


@dataclass(frozen=True)
class ProfectionEvent(BaseEvent):
    """Represents profected year transitions."""

    method: str
    house: int
    ruler: str
    end_ts: str
    midpoint_ts: str


@dataclass(frozen=True)
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
    """Represents a Vimśottarī dasha or sub-period."""

    parent: str | None = None


@dataclass(frozen=True)
class ZodiacalReleasingPeriod(TimelordPeriod):
    """Represents a zodiacal releasing period for a given lot."""

    lot: str
    sign: str
