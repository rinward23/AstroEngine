"""ICS export helpers for canonical transit events."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

from .canonical import TransitEvent, events_from_any

__all__ = [
    "canonical_events_to_ics",
    "ics_bytes_from_events",
    "write_ics_canonical",
]

_PRODID = "-//AstroEngine//Transit Scanner//EN"


def _escape_text(value: str) -> str:
    """Return ``value`` escaped for iCalendar text fields."""

    return (
        value.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(";", "\\;")
        .replace(",", "\\,")
    )


def _format_dt(ts: str) -> str:
    """Convert an ISO-8601 timestamp to ``YYYYMMDDTHHMMSSZ``."""

    moment = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)
    return moment.strftime("%Y%m%dT%H%M%SZ")


def _render_calendar(events: Sequence[TransitEvent], calendar_name: str) -> str:
    now_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{_PRODID}",
        f"NAME:{_escape_text(calendar_name)}",
        f"X-WR-CALNAME:{_escape_text(calendar_name)}",
    ]

    for event in events:
        dt_start = _format_dt(event.ts)
        summary = f"{event.moving} {event.aspect} {event.target}"
        description_bits = [
            f"Aspect: {event.aspect}",
            f"Orb: {event.orb:+.2f}°",
            f"Applying: {'yes' if event.applying else 'no'}",
        ]
        if event.score is not None:
            description_bits.append(f"Score: {event.score:.2f}")
        if event.meta:
            description_bits.append(
                "Meta: " + json.dumps(event.meta, sort_keys=True, ensure_ascii=False)
            )
        description = "\n".join(description_bits)

        uid_source = f"{dt_start}|{summary}|{event.orb}|{event.score}|{event.meta!r}".encode(
            "utf-8"
        )
        uid = hashlib.sha1(uid_source).hexdigest()

        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uid}@astroengine",
                f"DTSTAMP:{now_stamp}",
                f"DTSTART:{dt_start}",
                f"SUMMARY:{_escape_text(summary)}",
                f"DESCRIPTION:{_escape_text(description)}",
                "END:VEVENT",
            ]
        )

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def canonical_events_to_ics(
    events: Iterable[object],
    *,
    calendar_name: str = "AstroEngine Events",
) -> str:
    """Return an ICS string for ``events`` using canonical adapters."""

    canonical_events = events_from_any(events)
    return _render_calendar(canonical_events, calendar_name)


def ics_bytes_from_events(
    events: Iterable[object],
    *,
    calendar_name: str = "AstroEngine Events",
) -> bytes:
    """Return ICS bytes suitable for downloads."""

    payload = canonical_events_to_ics(events, calendar_name=calendar_name)
    return payload.encode("utf-8")


def write_ics_canonical(
    path: str | Path,
    events: Iterable[object],
    *,
    calendar_name: str = "AstroEngine Events",
) -> int:
    """Write ``events`` to ``path`` in ICS format and return the event count."""

    canonical_events = events_from_any(events)
    ics_payload = _render_calendar(canonical_events, calendar_name)
    Path(path).write_text(ics_payload, encoding="utf-8")
    return len(canonical_events)
