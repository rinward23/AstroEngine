"""Minimal ICS exporter for AstroEngine event records."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence
import uuid


def _to_ics_ts(ts: str) -> str:
    dt = datetime.fromisoformat(ts.replace('Z', '+00:00')).astimezone(timezone.utc)
    return dt.strftime('%Y%m%dT%H%M%SZ')


def _lines_for_event(ev) -> Sequence[str]:
    ts = getattr(ev, 'ts', None)
    if not ts:
        return []
    start = _to_ics_ts(str(ts))
    dtstamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    summary = getattr(ev, 'event_type', 'event')
    summary = str(summary).replace('\n', ' ').strip() or 'event'
    details = []
    for key in ('method', 'moving_body', 'static_body', 'aspect', 'kind', 'body', 'sign', 'lord', 'start_ts', 'end_ts'):
        value = getattr(ev, key, None)
        if value is not None and value != '':
            details.append(f"{key}: {value}")
    description = '\\n'.join(details)
    uid = f"{uuid.uuid4()}@astroengine"
    return [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART:{start}",
        f"SUMMARY:{summary}",
        f"DESCRIPTION:{description}" if description else "DESCRIPTION:",
        "END:VEVENT",
    ]


def write_ics(events: Iterable[object], path: str, title: str = "AstroEngine Events") -> None:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//AstroEngine//EN",
        f"X-WR-CALNAME:{title}",
    ]
    for ev in events:
        lines.extend(_lines_for_event(ev))
    lines.append("END:VCALENDAR")
    text = "\r\n".join(lines) + "\r\n"
    Path(path).write_text(text, encoding="utf-8")
