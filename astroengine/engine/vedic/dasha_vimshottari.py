"""Vimśottarī dasha computations with configurable profiles."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Sequence

from ...chart.natal import NatalChart
from .chart import VedicChartContext
from .nakshatra import (
    NAKSHATRA_ARC_DEGREES,
    NakshatraPosition,
    position_for,
)

__all__ = [
    "DashaPeriod",
    "VimshottariOptions",
    "build_vimshottari",
    "vimshottari_sequence",
]


ORDER: Sequence[tuple[str, float]] = (
    ("Ketu", 7.0),
    ("Venus", 20.0),
    ("Sun", 6.0),
    ("Moon", 10.0),
    ("Mars", 7.0),
    ("Rahu", 18.0),
    ("Jupiter", 16.0),
    ("Saturn", 19.0),
    ("Mercury", 17.0),
)
TOTAL_YEARS = sum(duration for _, duration in ORDER)

_LEVEL_BY_DEPTH = {
    1: "maha",
    2: "antar",
    3: "pratyantar",
    4: "sookshma",
    5: "praan",
}


@dataclass(frozen=True)
class DashaPeriod:
    """Represents a single dasha span in absolute time."""

    system: str
    level: str
    ruler: str
    start: datetime
    end: datetime
    metadata: dict[str, object]

    def span_days(self) -> float:
        return (self.end - self.start).total_seconds() / 86400.0


@dataclass(frozen=True)
class VimshottariOptions:
    """Runtime options that influence Vimśottarī calculations."""

    year_basis: float = 365.25
    anchor: str = "exact"

    def __post_init__(self) -> None:
        anchor = self.anchor.lower()
        if anchor not in {"exact", "midnight"}:
            raise ValueError("anchor must be 'exact' or 'midnight'")
        if self.year_basis <= 0.0:
            raise ValueError("year_basis must be positive")
        object.__setattr__(self, "anchor", anchor)


def vimshottari_sequence() -> Sequence[tuple[str, float]]:
    """Return the standard Vimśottarī maha-daśā order."""

    return ORDER


def _chart_from_context(chart: NatalChart | VedicChartContext) -> NatalChart:
    return chart.chart if isinstance(chart, VedicChartContext) else chart


def _limit_end(start: datetime, options: VimshottariOptions) -> datetime:
    return start + timedelta(days=TOTAL_YEARS * options.year_basis)


def _subdivide(
    periods: list[DashaPeriod],
    start: datetime,
    end: datetime,
    parent_ruler: str,
    *,
    level: int,
    max_level: int,
    options: VimshottariOptions,
) -> None:
    if level > max_level:
        return
    total_days = (end - start).total_seconds() / 86400.0
    if total_days <= 0.0:
        return
    cursor = start
    accumulator = 0.0
    for idx, (ruler, years) in enumerate(ORDER):
        accumulator += years
        if idx == len(ORDER) - 1:
            sub_end = end
        else:
            fraction = accumulator / TOTAL_YEARS
            sub_end = start + timedelta(days=total_days * fraction)
        parent_years = total_days / options.year_basis
        metadata = {
            "parent": parent_ruler,
            "span_years": parent_years * (years / TOTAL_YEARS),
        }
        level_name = _LEVEL_BY_DEPTH.get(level, f"level{level}")
        periods.append(
            DashaPeriod(
                system="vimshottari",
                level=level_name,
                ruler=ruler,
                start=cursor,
                end=sub_end,
                metadata=metadata,
            )
        )
        if level < max_level:
            _subdivide(
                periods,
                cursor,
                sub_end,
                ruler,
                level=level + 1,
                max_level=max_level,
                options=options,
            )
        cursor = sub_end


def _apply_anchor(moment: datetime, options: VimshottariOptions) -> datetime:
    if options.anchor == "midnight":
        return datetime(moment.year, moment.month, moment.day, tzinfo=moment.tzinfo)
    return moment


def _moon_position(chart: NatalChart) -> NakshatraPosition:
    try:
        moon = chart.positions["Moon"].longitude
    except KeyError as exc:  # pragma: no cover - validated upstream
        raise KeyError("Moon position is required for Vimśottarī dashas") from exc
    return position_for(moon)


def _starting_index(lord: str) -> int:
    for idx, (name, _) in enumerate(ORDER):
        if name.lower() == lord.lower():
            return idx
    raise ValueError(f"Unknown Vimśottarī ruler '{lord}'")


def build_vimshottari(
    chart: NatalChart | VedicChartContext,
    *,
    levels: int = 2,
    options: VimshottariOptions | None = None,
) -> list[DashaPeriod]:
    """Return Vimśottarī dashas covering 120 years from the birth moment."""

    if levels < 1 or levels > len(_LEVEL_BY_DEPTH):
        raise ValueError(
            f"levels must be between 1 and {len(_LEVEL_BY_DEPTH)}"
        )
    opts = options or VimshottariOptions()
    natal = _chart_from_context(chart)
    anchor_start = _apply_anchor(natal.moment, opts)

    moon_position = _moon_position(natal)
    start_index = _starting_index(moon_position.nakshatra.lord)
    fraction = (
        (moon_position.longitude % NAKSHATRA_ARC_DEGREES)
        / NAKSHATRA_ARC_DEGREES
    )
    remaining_fraction = 1.0 - fraction

    limit = _limit_end(anchor_start, opts)
    cursor = anchor_start
    sequence_index = start_index
    first_period = True
    periods: list[DashaPeriod] = []

    while cursor < limit:
        ruler, years = ORDER[sequence_index % len(ORDER)]
        if first_period:
            span_years = years * remaining_fraction
            first_period = False
        else:
            span_years = years
        if span_years <= 0.0:
            sequence_index += 1
            continue
        delta_days = span_years * opts.year_basis
        end = cursor + timedelta(days=delta_days)
        if end > limit:
            end = limit
        actual_years = (end - cursor).total_seconds() / 86400.0 / opts.year_basis
        metadata: dict[str, object] = {
            "span_years": actual_years,
            "sequence_index": sequence_index % len(ORDER),
        }
        if not periods:
            metadata.update(
                {
                    "janma_nakshatra": moon_position.nakshatra.name,
                    "janma_pada": moon_position.pada,
                    "balance_years": actual_years,
                }
            )
        periods.append(
            DashaPeriod(
                system="vimshottari",
                level="maha",
                ruler=ruler,
                start=cursor,
                end=end,
                metadata=metadata,
            )
        )
        if levels >= 2:
            _subdivide(
                periods,
                cursor,
                end,
                ruler,
                level=2,
                max_level=levels,
                options=opts,
            )
        cursor = end
        sequence_index += 1
        if cursor >= limit:
            break

    return periods
