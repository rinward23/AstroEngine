"""Solar arc directed chart helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Mapping, Sequence

from .config import ChartConfig
from .natal import NatalChart, DEFAULT_BODIES
from ..ephemeris import SwissEphemerisAdapter

__all__ = ["DirectedChart", "compute_solar_arc_chart"]

SIDEREAL_YEAR_DAYS = 365.2422


@dataclass(frozen=True)
class DirectedChart:
    """Solar arc directed positions derived from a natal chart."""

    target_moment: datetime
    arc_degrees: float
    positions: Mapping[str, float]


def _ensure_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


def compute_solar_arc_chart(
    natal_chart: NatalChart,
    target_moment: datetime,
    *,
    bodies: Sequence[str] | None = None,
    config: ChartConfig | None = None,
    adapter: SwissEphemerisAdapter | None = None,
) -> DirectedChart:
    """Return solar arc directed longitudes for ``target_moment``."""

    chart_config = config or ChartConfig()
    adapter = adapter or SwissEphemerisAdapter.from_chart_config(chart_config)
    natal_moment = _ensure_utc(natal_chart.moment)
    target_moment = _ensure_utc(target_moment)
    elapsed_days = (target_moment - natal_moment).total_seconds() / 86400.0
    progressed_dt = natal_moment + timedelta(days=elapsed_days / SIDEREAL_YEAR_DAYS)
    progressed_jd = adapter.julian_day(progressed_dt)

    if "Sun" not in natal_chart.positions:
        raise ValueError("Solar arc directions require the natal Sun position")

    natal_sun = natal_chart.positions["Sun"].longitude
    sun_code = DEFAULT_BODIES.get("Sun")
    if sun_code is None:
        raise ValueError("DEFAULT_BODIES missing Sun entry for solar arc computation")
    progressed_sun = adapter.body_position(progressed_jd, sun_code, body_name="Sun").longitude
    arc = (progressed_sun - natal_sun) % 360.0

    selected = set(natal_chart.positions.keys()) if bodies is None else {
        body for body in bodies if body in natal_chart.positions
    }
    if not selected:
        raise ValueError("No overlapping bodies to direct")

    directed_positions = {
        body: (natal_chart.positions[body].longitude + arc) % 360.0 for body in sorted(selected)
    }

    return DirectedChart(target_moment=target_moment, arc_degrees=arc, positions=directed_positions)
