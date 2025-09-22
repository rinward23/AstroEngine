"""Secondary progression helpers backed by Swiss Ephemeris."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Mapping, Sequence

from ..chart.config import ChartConfig
from ..chart.natal import DEFAULT_BODIES
from ..ephemeris import SwissEphemerisAdapter
from ..events import ProgressionEvent

__all__ = ["secondary_progressions"]

SIDEREAL_YEAR_DAYS = 365.2422


def _parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)


def _iso(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _resolve_bodies(names: Sequence[str] | None) -> Mapping[str, int]:
    if names is None:
        return DEFAULT_BODIES
    mapping = {name: DEFAULT_BODIES[name] for name in names if name in DEFAULT_BODIES}
    if not mapping:
        raise ValueError("No recognised bodies provided for progressions")
    return mapping


def secondary_progressions(
    natal_iso: str,
    start_iso: str,
    end_iso: str,
    *,
    bodies: Sequence[str] | None = None,
    step_days: float = 30.0,
    config: ChartConfig | None = None,
) -> list[ProgressionEvent]:
    """Return secondary progression samples between ``start`` and ``end``."""

    natal_dt = _parse_iso(natal_iso)
    start_dt = _parse_iso(start_iso)
    end_dt = _parse_iso(end_iso)
    if end_dt <= start_dt:
        return []

    chart_config = config or ChartConfig()
    adapter = SwissEphemerisAdapter.from_chart_config(chart_config)
    body_map = _resolve_bodies(bodies)

    events: list[ProgressionEvent] = []
    current = start_dt
    step_delta = timedelta(days=step_days)

    while current <= end_dt:
        elapsed_days = (current - natal_dt).total_seconds() / 86400.0
        progressed_offset_days = elapsed_days / SIDEREAL_YEAR_DAYS
        progressed_dt = natal_dt + timedelta(days=progressed_offset_days)
        progressed_jd = adapter.julian_day(progressed_dt)
        progressed_positions = adapter.body_positions(progressed_jd, body_map)
        positions = {name: pos.longitude % 360.0 for name, pos in progressed_positions.items()}

        events.append(
            ProgressionEvent(
                ts=_iso(current),
                jd=adapter.julian_day(current),
                method="secondary",
                positions=positions,
            )
        )

        current += step_delta

    events.sort(key=lambda event: event.jd)
    return events
