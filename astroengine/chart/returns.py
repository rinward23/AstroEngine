"""Return chart helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Mapping, Sequence

from .config import ChartConfig
from .natal import (
    ChartLocation,
    NatalChart,
    compute_natal_chart,
    DEFAULT_BODIES,
)
from ..detectors.returns import solar_lunar_returns
from ..events import ReturnEvent
from ..ephemeris import SwissEphemerisAdapter
from ..scoring import DEFAULT_ASPECTS, OrbCalculator

__all__ = ["ReturnChart", "compute_return_chart"]


@dataclass(frozen=True)
class ReturnChart:
    """Return chart tied to a solar or lunar return event."""

    kind: str
    event: ReturnEvent
    chart: NatalChart
    location: ChartLocation


def _ensure_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


def _safe_replace_year(moment: datetime, year: int) -> datetime:
    try:
        return moment.replace(year=year)
    except ValueError:
        if moment.month == 2 and moment.day == 29:
            return moment.replace(year=year, day=28)
        raise


def compute_return_chart(
    natal_chart: NatalChart,
    target_year: int,
    *,
    kind: str = "solar",
    location: ChartLocation | None = None,
    bodies: Mapping[str, int] | None = None,
    aspect_angles: Sequence[int] | None = None,
    orb_profile: str = "standard",
    chart_config: ChartConfig | None = None,
    adapter: SwissEphemerisAdapter | None = None,
    orb_calculator: OrbCalculator | None = None,
) -> ReturnChart:
    """Compute the solar or lunar return chart for ``target_year``."""

    adapter = adapter or SwissEphemerisAdapter(chart_config=chart_config)
    orb_calculator = orb_calculator or OrbCalculator()
    location = location or natal_chart.location
    body_map = bodies or DEFAULT_BODIES
    angles = aspect_angles or DEFAULT_ASPECTS

    natal_jd = adapter.julian_day(_ensure_utc(natal_chart.moment))
    start_dt = _safe_replace_year(_ensure_utc(natal_chart.moment), target_year)
    end_dt = _safe_replace_year(_ensure_utc(natal_chart.moment), target_year + 1)

    start_jd = adapter.julian_day(start_dt)
    end_jd = adapter.julian_day(end_dt)
    events = solar_lunar_returns(natal_jd, start_jd, end_jd, kind)
    if not events:
        raise ValueError(f"No {kind} return found between {start_dt.isoformat()} and {end_dt.isoformat()}")

    # Pick the event closest to the anniversary within the search window.
    event = min(events, key=lambda ev: abs(ev.jd - start_jd))
    event_dt = datetime.fromisoformat(event.ts.replace("Z", "+00:00")).astimezone(UTC)

    chart = compute_natal_chart(
        event_dt,
        location,
        bodies=body_map,
        aspect_angles=angles,
        orb_profile=orb_profile,
        chart_config=chart_config,
        adapter=adapter,
        orb_calculator=orb_calculator,
    )

    return ReturnChart(kind=kind.lower(), event=event, chart=chart, location=location)
