"""Utilities for generating RFC-5545 VTIMEZONE components."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

if False:  # pragma: no cover - typing helper
    from .ics import CalendarEvent


@dataclass
class _Transition:
    moment: datetime
    offset_from: timedelta
    offset_to: timedelta
    name_from: str
    name_to: str

    @property
    def component(self) -> str:
        # Determine whether the transition ends in daylight time.
        return "DAYLIGHT" if self.offset_to > self.offset_from else "STANDARD"


def build_vtimezone(tzid: str, events: Sequence[CalendarEvent]) -> list[str]:
    """Return a list of ICS lines describing ``tzid`` for the event window."""

    if not events:
        return []

    tz = ZoneInfo(tzid)
    start, end = _window(events)
    start_local = start.astimezone(tz)
    end_local = end.astimezone(tz)

    transitions = _collect_transitions(tz, start_local, end_local)
    if not transitions:
        offset = tz.utcoffset(start_local) or timedelta(0)
        name = tz.tzname(start_local) or tzid
        return [
            "BEGIN:VTIMEZONE",
            f"TZID:{tzid}",
            "BEGIN:STANDARD",
            f"DTSTART:{start_local.strftime('%Y%m%dT%H%M%S')}",
            f"TZOFFSETFROM:{_format_offset(offset)}",
            f"TZOFFSETTO:{_format_offset(offset)}",
            f"TZNAME:{name}",
            "END:STANDARD",
            "END:VTIMEZONE",
        ]

    lines = ["BEGIN:VTIMEZONE", f"TZID:{tzid}"]
    for transition in transitions:
        block_type = transition.component
        local_moment = transition.moment.astimezone(tz)
        lines.extend(
            [
                f"BEGIN:{block_type}",
                f"DTSTART:{local_moment.strftime('%Y%m%dT%H%M%S')}",
                f"TZOFFSETFROM:{_format_offset(transition.offset_from)}",
                f"TZOFFSETTO:{_format_offset(transition.offset_to)}",
                f"TZNAME:{transition.name_to}",
                "END:DAYLIGHT" if block_type == "DAYLIGHT" else "END:STANDARD",
            ]
        )
    lines.append("END:VTIMEZONE")
    return lines


def _window(events: Sequence[CalendarEvent]) -> tuple[datetime, datetime]:
    earliest = datetime.max.replace(tzinfo=UTC)
    latest = datetime.min.replace(tzinfo=UTC)
    for event in events:
        start = getattr(event, "start", None)
        end = getattr(event, "end", None)
        if start is not None:
            dt_start = _ensure_datetime(start)
            if dt_start < earliest:
                earliest = dt_start
        if end is not None:
            dt_end = _ensure_datetime(end)
            if dt_end > latest:
                latest = dt_end
    if latest <= earliest:
        latest = earliest + timedelta(days=1)
    return earliest, latest


def _ensure_datetime(value) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
    text = str(value)
    if text.endswith("Z"):
        text = text.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _collect_transitions(tz: ZoneInfo, start: datetime, end: datetime) -> list[_Transition]:
    # Expand window to capture boundary transitions.
    cursor = start - timedelta(days=370)
    stop = end + timedelta(days=370)
    transitions: list[_Transition] = []
    previous_offset = tz.utcoffset(cursor) or timedelta(0)
    previous_name = tz.tzname(cursor) or tz.key
    while cursor < stop:
        cursor += timedelta(days=1)
        current_offset = tz.utcoffset(cursor) or timedelta(0)
        current_name = tz.tzname(cursor) or tz.key
        if current_offset != previous_offset or current_name != previous_name:
            moment = _bisect_transition(tz, cursor - timedelta(days=1), cursor)
            transitions.append(
                _Transition(
                    moment=moment,
                    offset_from=previous_offset,
                    offset_to=current_offset,
                    name_from=previous_name,
                    name_to=current_name,
                )
            )
            previous_offset = current_offset
            previous_name = current_name
    return transitions


def _bisect_transition(tz: ZoneInfo, lower: datetime, upper: datetime) -> datetime:
    while (upper - lower) > timedelta(minutes=1):
        midpoint = lower + (upper - lower) / 2
        if tz.utcoffset(midpoint) == tz.utcoffset(lower):
            lower = midpoint
        else:
            upper = midpoint
    return upper


def _format_offset(delta: timedelta) -> str:
    total_seconds = int(delta.total_seconds())
    sign = "+" if total_seconds >= 0 else "-"
    total_seconds = abs(total_seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    return f"{sign}{hours:02d}{minutes:02d}"
