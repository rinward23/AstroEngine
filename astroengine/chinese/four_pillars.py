"""Four Pillars (BaZi) computation logic."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, tzinfo
from typing import Mapping, Sequence

from ..chart.natal import ChartLocation
from .constants import HeavenlyStem, EarthlyBranch
from .sexagenary import (
    SexagenaryCycleEntry,
    day_cycle_index,
    hour_cycle_index,
    month_cycle_index,
    sexagenary_entry_for_index,
    year_cycle_index,
)


@dataclass(frozen=True)
class Pillar:
    """A single pillar made up of a Heavenly Stem and Earthly Branch."""

    stem: HeavenlyStem
    branch: EarthlyBranch
    cycle_index: int

    def label(self) -> str:
        return sexagenary_entry_for_index(self.cycle_index).label()


@dataclass(frozen=True)
class FourPillarsChart:
    """Container for the year, month, day, and hour pillars."""

    moment: datetime
    location: ChartLocation | None
    timezone: tzinfo | None
    pillars: Mapping[str, Pillar]
    provenance: Mapping[str, object]

    def ordered_pillars(self) -> Sequence[Pillar]:
        return (
            self.pillars["year"],
            self.pillars["month"],
            self.pillars["day"],
            self.pillars["hour"],
        )


def _build_pillar(entry: SexagenaryCycleEntry) -> Pillar:
    return Pillar(
        stem=entry.stem,
        branch=entry.branch,
        cycle_index=entry.index,
    )


def compute_four_pillars(
    moment: datetime,
    location: ChartLocation | None = None,
    *,
    timezone: tzinfo | None = None,
) -> FourPillarsChart:
    """Compute the Four Pillars for ``moment``.

    Parameters
    ----------
    moment:
        Datetime representing the event (ideally timezone-aware).
    location:
        Optional :class:`~astroengine.chart.natal.ChartLocation` for provenance.
    timezone:
        Override timezone used for solar year/month calculations. When omitted,
        the timezone embedded in ``moment`` (if any) is used; naive datetimes
        default to UTC.
    """

    year_index = year_cycle_index(moment, tz=timezone)
    month_index = month_cycle_index(moment, tz=timezone)
    day_index = day_cycle_index(moment, tz=timezone)
    hour_index = hour_cycle_index(moment, tz=timezone)

    pillars = {
        "year": _build_pillar(sexagenary_entry_for_index(year_index)),
        "month": _build_pillar(sexagenary_entry_for_index(month_index)),
        "day": _build_pillar(sexagenary_entry_for_index(day_index)),
        "hour": _build_pillar(sexagenary_entry_for_index(hour_index)),
    }

    provenance: dict[str, object] = {
        "timezone": str(timezone) if timezone else str(moment.tzinfo or "UTC"),
        "solar_year_index": year_index,
        "solar_month_index": month_index,
        "reference_day_index": day_index,
    }

    return FourPillarsChart(
        moment=moment,
        location=location,
        timezone=timezone or moment.tzinfo,
        pillars=pillars,
        provenance=provenance,
    )


__all__ = ["Pillar", "FourPillarsChart", "compute_four_pillars"]
