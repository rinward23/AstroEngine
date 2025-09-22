"""Directions detector implementing solar arc directions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Mapping, Sequence

from ..chart.natal import DEFAULT_BODIES
from ..ephemeris import SwissEphemerisAdapter
from ..events import DirectionEvent

__all__ = ["solar_arc_directions"]


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
        raise ValueError("No recognised bodies provided for directions")
    return mapping


def _advance_year(dt: datetime) -> datetime:
    try:
        return dt.replace(year=dt.year + 1)
    except ValueError:
        return dt.replace(month=2, day=28, year=dt.year + 1)


def solar_arc_directions(
    natal_iso: str,
    start_iso: str,
    end_iso: str,
    *,
    bodies: Sequence[str] | None = None,
) -> list[DirectionEvent]:
    """Return solar arc directions sampled annually between ``start`` and ``end``."""

    natal_dt = _parse_iso(natal_iso)
    start_dt = _parse_iso(start_iso)
    end_dt = _parse_iso(end_iso)
    if end_dt <= start_dt:
        return []

    adapter = SwissEphemerisAdapter()
    body_map = _resolve_bodies(bodies)

    natal_jd = adapter.julian_day(natal_dt)
    natal_positions = adapter.body_positions(natal_jd, body_map)
    natal_sun = adapter.body_position(natal_jd, DEFAULT_BODIES["Sun"], body_name="Sun").longitude

    events: list[DirectionEvent] = []
    current = start_dt
    while current <= end_dt:
        elapsed_days = (current - natal_dt).total_seconds() / 86400.0
        progressed_offset_days = elapsed_days / SIDEREAL_YEAR_DAYS
        progressed_dt = natal_dt + timedelta(days=progressed_offset_days)
        progressed_jd = adapter.julian_day(progressed_dt)
        progressed_sun = adapter.body_position(
            progressed_jd, DEFAULT_BODIES["Sun"], body_name="Sun"
        ).longitude

        arc = (progressed_sun - natal_sun) % 360.0
        directed_positions = {
            name: (pos.longitude + arc) % 360.0 for name, pos in natal_positions.items()
        }

        events.append(
            DirectionEvent(
                ts=_iso(current),
                jd=adapter.julian_day(current),
                method="solar_arc",
                arc_degrees=arc,
                positions=directed_positions,
            )
        )

        current = _advance_year(current)

    events.sort(key=lambda event: event.jd)
    return events
