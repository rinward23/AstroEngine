"""Canonical event dataclasses shared across AstroEngine modules."""

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
    """Represents a lunation event (new or full Moon)."""

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
    sign_from: str
    sign_to: str
    longitude: float
    speed_longitude: float
    retrograde: bool

    @property
    def sign(self) -> str:
        """Return the destination sign for backward compatibility."""

        return self.sign_to

    @property
    def from_sign(self) -> str:
        """Alias for the departing sign used by older APIs."""

        return self.sign_from

    @property
    def to_sign(self) -> str:
        """Alias for the destination sign used by older APIs."""

        return self.sign_to

    @property
    def motion(self) -> str:
        """Return the textual motion descriptor expected by older callers."""

        return "retrograde" if self.retrograde else "direct"

    @property
    def speed_deg_per_day(self) -> float:
        """Expose the longitudinal speed in degrees/day for legacy consumers."""

        return self.speed_longitude


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

class IngressEvent(BaseEvent):
    """Represents a zodiac sign ingress for a moving body.

    The class serves both the classic ingress detector (which exposes
    ``sign``/``sign_index``) and the more detailed mundane ingress
    detector (which exposes ``from_sign``/``to_sign`` and motion data).
    Optional fields default to ``None`` so callers can progressively
    adopt the richer schema without breaking existing consumers.
    """

    body: str
    longitude: float
    sign: str | None = None
    sign_index: int | None = None
    from_sign: str | None = None
    to_sign: str | None = None
    motion: str | None = None
    speed_deg_per_day: float | None = None
    speed_longitude: float | None = None
    retrograde: bool | None = None

    def __post_init__(self) -> None:
        # Normalise speed aliases so downstream code can rely on either
        # attribute regardless of how the event was instantiated.
        if self.speed_deg_per_day is None and self.speed_longitude is not None:
            object.__setattr__(self, "speed_deg_per_day", self.speed_longitude)
        elif self.speed_longitude is None and self.speed_deg_per_day is not None:
            object.__setattr__(self, "speed_longitude", self.speed_deg_per_day)

        # Derive motion + retrograde flags when possible.
        if self.motion is None and self.speed_deg_per_day is not None:
            motion = "retrograde" if self.speed_deg_per_day < 0 else "direct"
            object.__setattr__(self, "motion", motion)
        if self.retrograde is None and self.motion is not None:
            object.__setattr__(self, "retrograde", self.motion.lower() == "retrograde")

        # Ensure legacy ``sign`` accessors remain populated when the
        # mundane detector supplies ``to_sign`` only.
        if self.sign is None and self.to_sign is not None:
            object.__setattr__(self, "sign", self.to_sign)
        if self.to_sign is None and self.sign is not None:
            object.__setattr__(self, "to_sign", self.sign)

    @property
    def sign_from(self) -> str | None:
        """Backwards compatible alias for :attr:`from_sign`."""

        return self.from_sign

    @property
    def sign_to(self) -> str | None:
        """Backwards compatible alias for :attr:`to_sign`."""

        return self.to_sign


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
    """Represents a Vimśottarī daśā or sub-period."""

    parent: str | None = None


@dataclass(frozen=True)
class ZodiacalReleasingPeriod(TimelordPeriod):
    """Represents a zodiacal releasing period for a given lot."""

    lot: str
    sign: str

