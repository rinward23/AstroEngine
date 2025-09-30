"""Dataclasses shared across the traditional timing engines."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from ...chart.natal import ChartLocation, NatalChart

__all__ = [
    "AlcocodenResult",
    "ChartCtx",
    "GeoLocation",
    "HylegResult",
    "Interval",
    "LifeProfile",
    "LifeSpanTable",
    "ProfectionSegment",
    "ProfectionState",
    "SectInfo",
    "ZRPeriod",
    "ZRTimeline",
    "build_chart_context",
]

GeoLocation = ChartLocation


@dataclass(frozen=True)
class Interval:
    """Half-open time interval used for timeline calculations."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.start.tzinfo is None or self.start.tzinfo.utcoffset(self.start) is None:
            raise ValueError("Interval.start must be timezone-aware")
        if self.end.tzinfo is None or self.end.tzinfo.utcoffset(self.end) is None:
            raise ValueError("Interval.end must be timezone-aware")
        if self.end <= self.start:
            raise ValueError("Interval end must be after start")

    def contains(self, moment: datetime) -> bool:
        reference = moment.astimezone(UTC)
        return self.start <= reference < self.end


@dataclass(frozen=True)
class ProfectionSegment:
    """A profection period spanning a year or month."""

    start: datetime
    end: datetime
    house: int
    sign: str
    year_lord: str
    co_rulers: Mapping[str, Any]
    notes: tuple[str, ...] = field(default_factory=tuple)

    def duration_days(self) -> float:
        return (self.end - self.start).total_seconds() / 86400.0


@dataclass(frozen=True)
class ProfectionState:
    """Snapshot of the profected year and month at a moment."""

    moment: datetime
    year_house: int
    year_sign: str
    year_lord: str
    month_house: int
    month_sign: str
    month_lord: str
    co_rulers: Mapping[str, Any]


@dataclass(frozen=True)
class SectInfo:
    """Sect classification metadata for a chart."""

    is_day: bool
    luminary_of_sect: str
    malefic_of_sect: str
    benefic_of_sect: str
    sun_altitude_deg: float


@dataclass(frozen=True)
class ZRPeriod:
    """Single zodiacal releasing period at a given level."""

    level: int
    start: datetime
    end: datetime
    sign: str
    ruler: str
    lb: bool = False
    lb_from: str | None = None
    lb_to: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_row(self) -> dict[str, Any]:
        payload = {
            "level": self.level,
            "start": self.start.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "end": self.end.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "sign": self.sign,
            "ruler": self.ruler,
        }
        if self.lb:
            payload["loosing_of_bond"] = {
                "from": self.lb_from,
                "to": self.lb_to,
            }
        if self.metadata:
            payload["metadata"] = dict(self.metadata)
        return payload


@dataclass
class ZRTimeline:
    """Container for zodiacal releasing periods grouped by level."""

    levels: Mapping[int, tuple[ZRPeriod, ...]]
    lot: str
    source: Literal["Spirit", "Fortune"]

    def iter_level(self, level: int) -> Iterable[ZRPeriod]:
        return iter(self.levels.get(level, ()))

    def flatten(self) -> list[ZRPeriod]:
        rows: list[ZRPeriod] = []
        for key in sorted(self.levels):
            rows.extend(self.levels[key])
        return rows

    def to_table(self) -> list[dict[str, Any]]:
        return [period.to_row() for period in self.flatten()]


@dataclass(frozen=True)
class LifeSpanTable:
    """Indicative minor/mean/major year spans for classical rulers."""

    minor_years: int
    mean_years: int
    major_years: int


@dataclass(frozen=True)
class LifeProfile:
    """Configuration bundle for Hyleg/Alcocoden resolution."""

    house_candidates: tuple[int, ...] = (1, 7, 9, 10, 11)
    include_fortune: bool = False
    dignity_weights: Mapping[str, float] = field(
        default_factory=lambda: {
            "rulership": 4.0,
            "exaltation": 3.0,
            "triplicity": 2.0,
            "bounds": 1.5,
            "face": 1.0,
            "sect": 1.5,
            "angular": 1.0,
            "succedent": 0.5,
            "cadent": 0.25,
        }
    )
    lifespan_years: Mapping[str, LifeSpanTable] = field(
        default_factory=lambda: {
            "sun": LifeSpanTable(19, 69, 120),
            "moon": LifeSpanTable(25, 66, 108),
            "mercury": LifeSpanTable(20, 76, 91),
            "venus": LifeSpanTable(8, 45, 82),
            "mars": LifeSpanTable(15, 66, 79),
            "jupiter": LifeSpanTable(12, 45, 79),
            "saturn": LifeSpanTable(30, 43, 57),
        }
    )
    bounds_scheme: str = "egyptian"
    notes: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HylegResult:
    """Selected hyleg candidate and scoring trace."""

    body: str
    degree: float
    sign: str
    house: int
    score: float
    notes: tuple[str, ...]
    trace: tuple[tuple[str, float], ...]


@dataclass(frozen=True)
class AlcocodenResult:
    """Resolved Alcocoden metadata derived from the hyleg."""

    body: str
    method: str
    indicative_years: LifeSpanTable | None
    confidence: float
    notes: tuple[str, ...]
    trace: tuple[str, ...]


@dataclass(frozen=True)
class ChartCtx:
    """Runtime context bundling natal chart, sect, and derived lots."""

    natal: NatalChart
    sect: SectInfo
    lots: Mapping[str, float]
    house_system: str = "whole_sign"

    def lot(self, name: str, default: float | None = None) -> float | None:
        return self.lots.get(name, default)


def build_chart_context(
    chart: NatalChart,
    sect: SectInfo,
    lots: Mapping[str, float],
    *,
    house_system: str = "whole_sign",
) -> ChartCtx:
    """Construct a :class:`ChartCtx` with validated metadata."""

    return ChartCtx(natal=chart, sect=sect, lots=lots, house_system=house_system)
