"""ICS export helpers for relationship timeline events."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from datetime import UTC, datetime

from .engine import Event

__all__ = ["events_to_ics"]


_ASPECT_SYMBOLS: dict[int, str] = {
    0: "☌",
    30: "⚺",
    45: "∠",
    60: "⚹",
    72: "✶",
    90: "□",
    120: "△",
    135: "⚼",
    144: "✴",
    150: "⚻",
    180: "☍",
}


def _format_dt(moment: datetime) -> str:
    if moment.tzinfo is None:
        value = moment.replace(tzinfo=UTC)
    else:
        value = moment.astimezone(UTC)
    return value.strftime("%Y%m%dT%H%M%SZ")


def _aspect_symbol(aspect: int | None) -> str:
    if aspect is None:
        return ""
    return _ASPECT_SYMBOLS.get(aspect, f"{int(aspect)}°")


def _event_summary(event: Event, chart_type: str) -> str:
    if event.type == "return":
        return f"Return {event.transiter} ({chart_type})"
    symbol = _aspect_symbol(event.aspect)
    target = event.target or ""
    if symbol:
        return f"TR {event.transiter} {symbol} {chart_type} {target}".strip()
    return f"TR {event.transiter} {chart_type} {target}".strip()


def _event_description(event: Event) -> str:
    exact = event.exact_utc.astimezone(UTC).isoformat().replace(
        "+00:00", "Z"
    )
    fields = [
        f"Type: {event.type}",
        f"Transiter: {event.transiter}",
    ]
    if event.target:
        fields.append(f"Target: {event.target}")
    if event.aspect is not None:
        fields.append(f"Aspect: {event.aspect}°")
    fields.extend(
        [
            f"Exact: {exact}",
            f"Max severity: {event.max_severity:.3f}",
            f"Orb: {event.orb:.2f}°",
            f"Score: {event.score:.3f}",
        ]
    )
    return "\\n".join(fields)


def _event_uid(event: Event) -> str:
    payload = "|".join(
        [
            event.type,
            event.transiter,
            event.target or "-",
            str(event.aspect) if event.aspect is not None else "-",
            _format_dt(event.exact_utc),
        ]
    )
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()
    return f"{digest}@astroengine"


def events_to_ics(
    events: Iterable[Event],
    *,
    chart_type: str,
    calendar_name: str = "Relationship Timeline",
) -> str:
    """Render ``events`` into an RFC5545 (iCalendar) payload."""

    lines = [
        "BEGIN:VCALENDAR",
        "PRODID:-//Relationship Timelines//EN",
        "VERSION:2.0",
        f"X-WR-CALNAME:{calendar_name}",
    ]
    for event in events:
        dt_start = _format_dt(event.start_utc)
        dt_end = _format_dt(event.end_utc)
        summary = _event_summary(event, chart_type)
        description = _event_description(event)
        uid = _event_uid(event)
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTART:{dt_start}",
                f"DTEND:{dt_end}",
                f"SUMMARY:{summary}",
                "DESCRIPTION:" + description.replace("\n", "\\n"),
                "END:VEVENT",
            ]
        )

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
