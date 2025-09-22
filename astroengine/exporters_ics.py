"""ICS export utilities for AstroEngine."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Mapping

from .narrative import markdown_to_plaintext

__all__ = ["format_ics_calendar", "write_ics_calendar"]


def write_ics_calendar(
    path: str | Path,
    events: Iterable[object],
    *,
    title: str,
    narrative_text: object | None = None,
) -> int:
    """Write an ICS file for ``events`` and return the number of entries."""

    calendar = format_ics_calendar(events, title=title, narrative_text=narrative_text)
    target = Path(path)
    target.write_text(calendar, encoding="utf-8")
    return calendar.count("BEGIN:VEVENT")


def format_ics_calendar(
    events: Iterable[object],
    *,
    title: str,
    narrative_text: object | None = None,
) -> str:
    """Return an ICS calendar as a string."""

    event_list = list(events)
    sorted_events = sorted(
        event_list,
        key=lambda event: (
            _event_datetime(event),
            str(_event_attr(event, "kind") or ""),
            str(_event_attr(event, "moving") or ""),
            str(_event_attr(event, "target") or ""),
        ),
    )

    narrative_block = _prepare_narrative_block(narrative_text)

    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//AstroEngine//Narrative Calendar 1.0//EN",
        f"X-WR-CALNAME:{_escape_ics(str(title))}",
        "CALSCALE:GREGORIAN",
    ]

    for event in sorted_events:
        timestamp_iso = _event_timestamp(event)
        dtstart = _iso_to_ics(timestamp_iso)
        dtend = _iso_to_ics(timestamp_iso, delta_minutes=30)
        dtstamp = dtstart
        summary = _event_summary(event)
        description = _event_description(event, narrative_block)
        uid = _event_uid(event, timestamp_iso)

        lines.extend(
            [
                "BEGIN:VEVENT",
                *_fold_ics_line(f"UID:{uid}"),
                *_fold_ics_line(f"DTSTAMP:{dtstamp}"),
                *_fold_ics_line(f"DTSTART:{dtstart}"),
                *_fold_ics_line(f"DTEND:{dtend}"),
                *_fold_ics_line(f"SUMMARY:{_escape_ics(summary)}"),
            ]
        )
        if description:
            lines.extend(_fold_ics_line(f"DESCRIPTION:{_escape_ics(description)}"))
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def _prepare_narrative_block(narrative: object | None) -> str | None:
    if narrative is None:
        return None
    if hasattr(narrative, "markdown"):
        markdown = getattr(narrative, "markdown")
    else:
        markdown = str(narrative)
    if not markdown:
        return None
    return markdown_to_plaintext(str(markdown))


def _event_attr(event: object, key: str):
    if isinstance(event, Mapping):
        return event.get(key)
    return getattr(event, key, None)


def _event_timestamp(event: object) -> str:
    ts = _event_attr(event, "timestamp") or _event_attr(event, "when_iso") or ""
    if ts:
        return str(ts)
    ts = _event_attr(event, "ts")
    return str(ts) if ts else ""


def _event_datetime(event: object) -> datetime:
    timestamp = _event_timestamp(event)
    if not timestamp:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:  # pragma: no cover - defensive
        return datetime(1970, 1, 1, tzinfo=timezone.utc)


def _iso_to_ics(timestamp: str, *, delta_minutes: int = 0) -> str:
    if timestamp:
        try:
            base = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:  # pragma: no cover - defensive
            base = datetime(1970, 1, 1, tzinfo=timezone.utc)
    else:
        base = datetime(1970, 1, 1, tzinfo=timezone.utc)
    if delta_minutes:
        base = base + timedelta(minutes=delta_minutes)
    return base.strftime("%Y%m%dT%H%M%SZ")


def _event_summary(event: object) -> str:
    moving = _event_attr(event, "moving")
    target = _event_attr(event, "target")
    kind = _event_attr(event, "kind")
    pieces = [str(part).title() for part in (moving, kind, target) if part]
    return " ".join(pieces) if pieces else str(kind or "Transit Event").title()


def _event_description(event: object, narrative_block: str | None) -> str:
    lines: list[str] = []
    moving = _event_attr(event, "moving") or "-"
    target = _event_attr(event, "target") or "-"
    kind = _event_attr(event, "kind") or "-"
    orb_abs = _event_attr(event, "orb_abs")
    orb_allow = _event_attr(event, "orb_allow")
    phase = _event_attr(event, "applying_or_separating") or "-"
    score = _event_attr(event, "score")
    lines.append(f"Moving: {moving}")
    lines.append(f"Target: {target}")
    lines.append(f"Kind: {kind}")
    if orb_abs is not None and orb_allow is not None:
        try:
            lines.append(f"Orb: {float(orb_abs):.2f}° (allow {float(orb_allow):.2f}°)")
        except (TypeError, ValueError):  # pragma: no cover - defensive
            lines.append("Orb: unavailable")
    phase_text = str(phase).replace("_", " ").title()
    lines.append(f"Phase: {phase_text}")
    if score is not None:
        try:
            lines.append(f"Score: {float(score):.1f}")
        except (TypeError, ValueError):  # pragma: no cover - defensive
            pass
    metadata = _event_attr(event, "metadata")
    if isinstance(metadata, Mapping) and metadata:
        for key, value in metadata.items():
            lines.append(f"{str(key).title()}: {value}")
    if narrative_block:
        lines.append("")
        lines.append("Narrative Summary:")
        lines.extend(narrative_block.splitlines())
    return "\n".join(lines)


def _event_uid(event: object, timestamp: str) -> str:
    moving = _event_attr(event, "moving") or "-"
    target = _event_attr(event, "target") or "-"
    kind = _event_attr(event, "kind") or "-"
    score = _event_attr(event, "score") or 0.0
    payload = f"{timestamp}|{moving}|{target}|{kind}|{score}"
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()
    return f"{digest}@astroengine"


def _escape_ics(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _fold_ics_line(line: str) -> list[str]:
    if len(line) <= 75:
        return [line]
    segments: list[str] = []
    remaining = line
    while len(remaining) > 75:
        segments.append(remaining[:75])
        remaining = " " + remaining[75:]
    segments.append(remaining)
    return segments
