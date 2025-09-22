"""Progressed chart helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Mapping, Sequence

from .config import ChartConfig
from .natal import (
    ChartLocation,
    NatalChart,
    compute_natal_chart,
    DEFAULT_BODIES,
)
from ..ephemeris import SwissEphemerisAdapter
from ..scoring import DEFAULT_ASPECTS, OrbCalculator

__all__ = ["ProgressedChart", "compute_secondary_progressed_chart"]

SIDEREAL_YEAR_DAYS = 365.2422


@dataclass(frozen=True)
class ProgressedChart:
    """Container for a progressed chart and associated metadata."""

    target_moment: datetime
    progressed_moment: datetime
    chart: NatalChart


def _ensure_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


def compute_secondary_progressed_chart(
    natal_chart: NatalChart,
    target_moment: datetime,
    *,
    location: ChartLocation | None = None,
    bodies: Mapping[str, int] | None = None,
    aspect_angles: Sequence[int] | None = None,
    orb_profile: str = "standard",
    chart_config: ChartConfig | None = None,
    adapter: SwissEphemerisAdapter | None = None,
    orb_calculator: OrbCalculator | None = None,
) -> ProgressedChart:
    """Compute a secondary progressed chart for ``target_moment``."""

    adapter = adapter or SwissEphemerisAdapter(chart_config=chart_config)
    orb_calculator = orb_calculator or OrbCalculator()
    location = location or natal_chart.location
    body_map = bodies or DEFAULT_BODIES
    angles = aspect_angles or DEFAULT_ASPECTS

    natal_moment = _ensure_utc(natal_chart.moment)
    target_moment = _ensure_utc(target_moment)
    elapsed_days = (target_moment - natal_moment).total_seconds() / 86400.0
    progressed_offset = timedelta(days=elapsed_days / SIDEREAL_YEAR_DAYS)
    progressed_moment = natal_moment + progressed_offset

    progressed_chart = compute_natal_chart(
        progressed_moment,
        location,
        bodies=body_map,
        aspect_angles=angles,
        orb_profile=orb_profile,
        chart_config=chart_config,
        adapter=adapter,
        orb_calculator=orb_calculator,
    )

    return ProgressedChart(
        target_moment=target_moment,
        progressed_moment=progressed_moment,
        chart=progressed_chart,
    )
