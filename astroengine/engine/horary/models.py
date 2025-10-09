"""Typed containers used by the horary engine."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime

__all__ = [
    "GeoLocation",
    "PlanetaryHourResult",
    "DignityStatus",
    "Significator",
    "SignificatorSet",
    "ReceptionRecord",
    "AspectContact",
    "TranslationOfLight",
    "CollectionOfLight",
    "Prohibition",
    "RadicalityCheck",
    "JudgementContribution",
    "JudgementResult",
]


@dataclass(frozen=True)
class GeoLocation:
    """Geographic location supplied when casting the horary chart."""

    latitude: float
    longitude: float
    altitude: float = 0.0


@dataclass(frozen=True)
class PlanetaryHourResult:
    """Summary of the active planetary hour for the question moment."""

    ruler: str
    index: int
    start: datetime
    end: datetime
    sunrise: datetime
    sunset: datetime
    next_sunrise: datetime
    day_ruler: str
    sequence: tuple[str, ...]


@dataclass(frozen=True)
class DignityStatus:
    """Essential dignity or debility assigned to a significator."""

    domicile: str | None = None
    exaltation: str | None = None
    triplicity: str | None = None
    term: str | None = None
    face: str | None = None
    detriment: str | None = None
    fall: str | None = None
    score: float | None = None


@dataclass(frozen=True)
class Significator:
    """Represents a horary significator and its derived metadata."""

    body: str
    longitude: float
    latitude: float
    speed: float
    house: int
    dignities: DignityStatus
    receptions: Mapping[str, Sequence[str]]
    role: str


@dataclass(frozen=True)
class SignificatorSet:
    """Primary significators for the querent, quesited, and supporting bodies."""

    querent: Significator
    quesited: Significator
    moon: Significator
    co_significators: tuple[Significator, ...] = ()
    is_day_chart: bool = True


@dataclass(frozen=True)
class ReceptionRecord:
    """Describes reception between two bodies."""

    source: str
    target: str
    dignities: tuple[str, ...]


@dataclass(frozen=True)
class AspectContact:
    """Aspect contact details between two bodies."""

    body_a: str
    body_b: str
    aspect: str
    orb: float
    exact_delta: float
    applying: bool
    moving_body: str | None = None
    target_longitude: float | None = None
    perfection_time: datetime | None = None


@dataclass(frozen=True)
class TranslationOfLight:
    """Translation of light between two significators."""

    translator: str
    from_body: str
    to_body: str
    sequence: tuple[AspectContact, ...]


@dataclass(frozen=True)
class CollectionOfLight:
    """Collection of light by a slower body."""

    collector: str
    bodies: tuple[str, str]
    sequence: tuple[AspectContact, ...]


@dataclass(frozen=True)
class Prohibition:
    """Intervening aspect preventing perfection."""

    preventing_body: str
    affected_pair: tuple[str, str]
    contact: AspectContact


@dataclass(frozen=True)
class RadicalityCheck:
    """Result of a radicality policy check."""

    code: str
    flag: bool
    reason: str
    data: Mapping[str, object] = field(default_factory=dict)
    caution_weight: float | None = None


@dataclass(frozen=True)
class JudgementContribution:
    """Weighted contribution included in the final judgement."""

    code: str
    label: str
    weight: float
    value: float
    score: float
    rationale: str


@dataclass(frozen=True)
class JudgementResult:
    """Aggregated horary judgement score and qualitative class."""

    score: float
    classification: str
    contributions: tuple[JudgementContribution, ...]
