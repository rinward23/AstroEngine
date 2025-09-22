"""Progressions detector implementing secondary progressions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Mapping, Sequence

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


def _advance_year(dt: datetime) -> datetime:
    try:
        return dt.replace(year=dt.year + 1)
    except ValueError:
        # Handle February 29th by falling back to February 28th.
        return dt.replace(month=2, day=28, year=dt.year + 1)


def secondary_progressions(
    natal_iso: str,
    start_iso: str,
    end_iso: str,
    *,
    bodies: Sequence[str] | None = None,
) -> list[ProgressionEvent]:
    """Return secondary progression samples between ``start_iso`` and ``end_iso``."""

    natal_dt = _parse_iso(natal_iso)
    start_dt = _parse_iso(start_iso)
    end_dt = _parse_iso(end_iso)
    if end_dt <= start_dt:
        return []

    adapter = SwissEphemerisAdapter()
    body_map = _resolve_bodies(bodies)

    events: list[ProgressionEvent] = []
    current = start_dt
    while current <= end_dt:
        elapsed_days = (current - natal_dt).total_seconds() / 86400.0
        progressed_offset_days = elapsed_days / SIDEREAL_YEAR_DAYS
        progressed_dt = natal_dt + timedelta(days=progressed_offset_days)

        target_jd = adapter.julian_day(current)
        progressed_jd = adapter.julian_day(progressed_dt)
        positions = adapter.body_positions(progressed_jd, body_map)

        events.append(
            ProgressionEvent(
                ts=_iso(current),
                jd=target_jd,
                method="secondary",
                progressed_jd=progressed_jd,
                positions={name: pos.longitude for name, pos in positions.items()},
            )
        )

        current = _advance_year(current)

    events.sort(key=lambda event: event.jd)
    return events
