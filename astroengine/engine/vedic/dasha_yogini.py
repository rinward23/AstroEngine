"""Yoginī dasha (8-cycle) implementation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Sequence

from ...chart.natal import NatalChart
from .chart import VedicChartContext
from .dasha_vimshottari import DashaPeriod
from .nakshatra import NAKSHATRA_ARC_DEGREES, position_for

__all__ = ["build_yogini", "yogini_sequence"]


ORDER: Sequence[tuple[str, int]] = (
    ("Mangala", 1),
    ("Pingala", 2),
    ("Dhanya", 3),
    ("Bhramari", 4),
    ("Bhadrika", 5),
    ("Ulka", 6),
    ("Siddha", 7),
    ("Sankata", 8),
)
PLANET_MAP: dict[str, str] = {
    "Mangala": "Moon",
    "Pingala": "Sun",
    "Dhanya": "Jupiter",
    "Bhramari": "Mars",
    "Bhadrika": "Mercury",
    "Ulka": "Saturn",
    "Siddha": "Venus",
    "Sankata": "Rahu",
}
TOTAL_YEARS = sum(years for _, years in ORDER)


@dataclass(frozen=True)
class YoginiOptions:
    year_basis: float = 365.25

    def __post_init__(self) -> None:
        if self.year_basis <= 0.0:
            raise ValueError("year_basis must be positive")


def yogini_sequence() -> Sequence[tuple[str, int]]:
    return ORDER


def _chart(chart: NatalChart | VedicChartContext) -> NatalChart:
    return chart.chart if isinstance(chart, VedicChartContext) else chart


def _limit(moment: datetime, options: YoginiOptions) -> datetime:
    return moment + timedelta(days=TOTAL_YEARS * options.year_basis)


def _subdivide(
    periods: list[DashaPeriod],
    start: datetime,
    end: datetime,
    parent: str,
    *,
    level: int,
    max_level: int,
    options: YoginiOptions,
) -> None:
    if level > max_level:
        return
    total_days = (end - start).total_seconds() / 86400.0
    if total_days <= 0.0:
        return
    cursor = start
    accumulator = 0
    for idx, (name, years) in enumerate(ORDER):
        accumulator += years
        if idx == len(ORDER) - 1:
            sub_end = end
        else:
            fraction = accumulator / TOTAL_YEARS
            sub_end = start + timedelta(days=total_days * fraction)
        parent_years = total_days / options.year_basis
        span_years = parent_years * (years / TOTAL_YEARS)
        periods.append(
            DashaPeriod(
                system="yogini",
                level="antara" if level == 2 else f"l{level}",
                ruler=name,
                start=cursor,
                end=sub_end,
                metadata={"parent": parent, "span_years": span_years, "planet": PLANET_MAP[name]},
            )
        )
        if level < max_level:
            _subdivide(
                periods,
                cursor,
                sub_end,
                name,
                level=level + 1,
                max_level=max_level,
                options=options,
            )
        cursor = sub_end


def build_yogini(
    chart: NatalChart | VedicChartContext,
    *,
    levels: int = 2,
    options: YoginiOptions | None = None,
) -> list[DashaPeriod]:
    """Return Yoginī dasha periods for the first 36 years from birth."""

    if levels < 1 or levels > 3:
        raise ValueError("levels must be between 1 and 3")
    opts = options or YoginiOptions()
    natal = _chart(chart)
    moon_position = position_for(natal.positions["Moon"].longitude)
    start_index = moon_position.nakshatra.index % len(ORDER)
    fraction = (
        (moon_position.longitude % NAKSHATRA_ARC_DEGREES)
        / NAKSHATRA_ARC_DEGREES
    )
    remaining_fraction = 1.0 - fraction

    start = natal.moment
    limit = _limit(start, opts)
    cursor = start
    index = start_index
    first = True
    periods: list[DashaPeriod] = []

    while cursor < limit:
        name, years = ORDER[index % len(ORDER)]
        if first:
            span_years = years * remaining_fraction
            first = False
        else:
            span_years = years
        if span_years <= 0.0:
            index += 1
            continue
        delta_days = span_years * opts.year_basis
        end = cursor + timedelta(days=delta_days)
        if end > limit:
            end = limit
        actual_years = (end - cursor).total_seconds() / 86400.0 / opts.year_basis
        metadata = {
            "span_years": actual_years,
            "planet": PLANET_MAP[name],
            "sequence_index": index % len(ORDER),
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
                system="yogini",
                level="maha",
                ruler=name,
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
                name,
                level=2,
                max_level=levels,
                options=opts,
            )
        cursor = end
        index += 1
        if cursor >= limit:
            break

    return periods
