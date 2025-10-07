"""ICS calendar exports aligned with the AstroEngine normalized event model."""
from __future__ import annotations

import csv
import json
from collections.abc import Iterable, Mapping, MutableMapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from io import StringIO
from typing import Any
from zoneinfo import ZoneInfo

from .timezone_blocks import build_vtimezone

PRODID = "-//AstroEngine//Exports 1.0//EN"
DEFAULT_CALENDAR_NAME = "AstroEngine Events"


@dataclass(slots=True)
class Alarm:
    """Representation of an iCalendar ``VALARM`` entry."""

    trigger: str
    action: str = "DISPLAY"
    description: str | None = None
    duration: str | None = None
    repeat: int | None = None


@dataclass(slots=True)
class CalendarEvent:
    """Normalized calendar event for ICS/CSV export."""

    uid: str
    kind: str
    summary: str
    start: datetime | str
    end: datetime | str | None = None
    description: str | None = None
    all_day: bool = False
    location: str | None = None
    categories: Sequence[str] = field(default_factory=tuple)
    alarms: Sequence[Alarm] = field(default_factory=tuple)
    meta: Mapping[str, Any] = field(default_factory=dict)
    rdates: Sequence[datetime | str] = field(default_factory=tuple)
    rrule: str | None = None
    url: str | None = None
    status: str | None = None
    transparency: str | None = None
    priority: int | None = None
    created: datetime | str | None = None
    last_modified: datetime | str | None = None


EventLike = CalendarEvent | Mapping[str, Any]


def to_ics(
    events: Iterable[EventLike],
    tz: str | ZoneInfo | None = "UTC",
    calendar_name: str = DEFAULT_CALENDAR_NAME,
    *,
    color: str | None = None,
    generated_ts: datetime | None = None,
) -> bytes:
    """Return ICS bytes for ``events`` using the normalized export contract."""

    normalized = [_coerce_event(event) for event in events]
    tzinfo, tzid = _resolve_timezone(tz)
    dtstamp = (generated_ts or datetime.now(UTC)).astimezone(UTC)

    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PRODID}",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{_escape(calendar_name)}",
    ]
    if color:
        lines.append(f"X-APPLE-CALENDAR-COLOR:{color}")
    if tzid and tzid.upper() != "UTC":
        tz_block = build_vtimezone(tzid, normalized)
        if tz_block:
            lines.extend(tz_block)

    for event in normalized:
        lines.extend(_render_event(event, tzinfo, tzid, dtstamp))

    lines.append("END:VCALENDAR")
    payload = "\r\n".join(lines) + "\r\n"
    return payload.encode("utf-8")


def to_csv(events: Iterable[EventLike]) -> bytes:
    """Return CSV bytes mirroring the normalized event model."""

    normalized = [_coerce_event(event) for event in events]
    buffer = StringIO()
    fieldnames = [
        "uid",
        "kind",
        "summary",
        "description",
        "start",
        "end",
        "all_day",
        "location",
        "categories",
        "alarms",
        "meta",
        "rdates",
        "rrule",
        "url",
        "status",
        "transparency",
        "priority",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for event in normalized:
        writer.writerow(
            {
                "uid": event.uid,
                "kind": event.kind,
                "summary": event.summary,
                "description": event.description or "",
                "start": _to_iso(event.start),
                "end": _to_iso(event.end),
                "all_day": "true" if event.all_day else "false",
                "location": event.location or "",
                "categories": ",".join(event.categories),
                "alarms": json.dumps([_alarm_to_json(alarm) for alarm in event.alarms]),
                "meta": json.dumps(event.meta, sort_keys=True, ensure_ascii=False),
                "rdates": ",".join(_to_iso(value) for value in event.rdates),
                "rrule": event.rrule or "",
                "url": event.url or "",
                "status": event.status or "",
                "transparency": event.transparency or "",
                "priority": "" if event.priority is None else str(event.priority),
            }
        )
    return buffer.getvalue().encode("utf-8")


def _coerce_event(payload: EventLike) -> CalendarEvent:
    if isinstance(payload, CalendarEvent):
        return payload
    if not isinstance(payload, Mapping):  # pragma: no cover - defensive
        raise TypeError(f"Unsupported event payload: {payload!r}")
    data: MutableMapping[str, Any] = dict(payload)
    alarms_raw = data.get("alarms") or []
    alarms = [_coerce_alarm(alarm) for alarm in alarms_raw]
    categories = tuple(str(value) for value in data.get("categories") or [])
    meta = data.get("meta") or {}
    rdates_raw = data.get("rdates") or []
    return CalendarEvent(
        uid=str(data["uid"]),
        kind=str(data.get("kind", "event")),
        summary=str(data.get("summary", "")),
        description=data.get("description"),
        start=data.get("start"),
        end=data.get("end"),
        all_day=bool(data.get("all_day", False)),
        location=data.get("location"),
        categories=categories,
        alarms=tuple(alarms),
        meta=dict(meta),
        rdates=tuple(rdates_raw),
        rrule=data.get("rrule"),
        url=data.get("url"),
        status=data.get("status"),
        transparency=data.get("transparency"),
        priority=data.get("priority"),
        created=data.get("created"),
        last_modified=data.get("last_modified"),
    )


def _coerce_alarm(payload: Mapping[str, Any]) -> Alarm:
    if isinstance(payload, Alarm):  # pragma: no cover - handled earlier
        return payload
    return Alarm(
        trigger=str(payload["trigger"]),
        action=str(payload.get("action", "DISPLAY")),
        description=payload.get("description"),
        duration=payload.get("duration"),
        repeat=payload.get("repeat"),
    )


def _resolve_timezone(tz: str | ZoneInfo | None) -> tuple[ZoneInfo, str]:
    if isinstance(tz, ZoneInfo):
        return tz, getattr(tz, "key", "UTC") or "UTC"
    if tz in (None, "UTC", "utc"):
        return ZoneInfo("UTC"), "UTC"
    zone = ZoneInfo(str(tz))
    return zone, str(tz)


def _render_event(
    event: CalendarEvent,
    tzinfo: ZoneInfo,
    tzid: str,
    dtstamp: datetime,
) -> list[str]:
    lines = ["BEGIN:VEVENT"]
    dtstamp_formatted = dtstamp.strftime("%Y%m%dT%H%M%SZ")
    lines.extend(_fold(f"DTSTAMP:{dtstamp_formatted}"))
    lines.extend(_fold(f"UID:{_escape(event.uid)}"))
    lines.extend(_fold(f"SUMMARY:{_escape(event.summary)}"))

    start_fmt, start_utc = _format_event_dt(event.start, event.all_day, tzinfo, tzid)
    end_fmt, end_utc = _format_event_dt(event.end, event.all_day, tzinfo, tzid)

    if event.all_day:
        lines.extend(_fold(f"DTSTART;VALUE=DATE:{start_fmt}"))
        if end_fmt:
            lines.extend(_fold(f"DTEND;VALUE=DATE:{end_fmt}"))
        else:
            # all-day events default to a single day; DTEND is exclusive so add one day
            fallback = _format_date(_parse_datetime(event.start) + timedelta(days=1))
            lines.extend(_fold(f"DTEND;VALUE=DATE:{fallback}"))
    else:
        if start_utc:
            lines.extend(_fold(f"DTSTART:{start_fmt}"))
        else:
            lines.extend(_fold(f"DTSTART;TZID={tzid}:{start_fmt}"))
        if end_fmt:
            if end_utc:
                lines.extend(_fold(f"DTEND:{end_fmt}"))
            else:
                lines.extend(_fold(f"DTEND;TZID={tzid}:{end_fmt}"))

    if event.description:
        lines.extend(_fold(f"DESCRIPTION:{_escape(event.description)}"))
    if event.location:
        lines.extend(_fold(f"LOCATION:{_escape(event.location)}"))
    if event.categories:
        categories = ",".join(_escape(cat) for cat in event.categories)
        lines.extend(_fold(f"CATEGORIES:{categories}"))
    if event.url:
        lines.extend(_fold(f"URL:{_escape(event.url)}"))
    if event.status:
        lines.extend(_fold(f"STATUS:{_escape(event.status)}"))
    if event.transparency:
        lines.extend(_fold(f"TRANSP:{_escape(event.transparency)}"))
    if event.priority is not None:
        lines.extend(_fold(f"PRIORITY:{int(event.priority)}"))
    if event.created:
        created_dt = _parse_datetime(event.created).astimezone(UTC)
        lines.extend(_fold(f"CREATED:{created_dt.strftime('%Y%m%dT%H%M%SZ')}"))
    if event.last_modified:
        modified_dt = _parse_datetime(event.last_modified).astimezone(UTC)
        lines.extend(_fold(f"LAST-MODIFIED:{modified_dt.strftime('%Y%m%dT%H%M%SZ')}"))

    lines.extend(_fold(f"X-ASTROENGINE-KIND:{_escape(event.kind)}"))
    if event.meta:
        meta_text = json.dumps(event.meta, sort_keys=True, ensure_ascii=False)
        lines.extend(_fold(f"X-ASTROENGINE-META:{_escape(meta_text)}"))

    if event.rdates:
        if event.all_day:
            all_day_values: list[str] = []
            for value in event.rdates:
                formatted, _ = _format_event_dt(value, True, tzinfo, tzid)
                if formatted:
                    all_day_values.append(formatted)
            if all_day_values:
                lines.extend(_fold(f"RDATE;VALUE=DATE:{','.join(all_day_values)}"))
        else:
            utc_values: list[str] = []
            local_values: list[str] = []
            for value in event.rdates:
                formatted, is_utc = _format_event_dt(value, False, tzinfo, tzid)
                if formatted is None:
                    continue
                if is_utc:
                    utc_values.append(formatted)
                else:
                    local_values.append(formatted)
            if utc_values:
                lines.extend(_fold(f"RDATE:{','.join(utc_values)}"))
            if local_values:
                lines.extend(_fold(f"RDATE;TZID={tzid}:{','.join(local_values)}"))
    if event.rrule:
        lines.extend(_fold(f"RRULE:{event.rrule}"))

    for alarm in event.alarms:
        lines.append("BEGIN:VALARM")
        lines.extend(_fold(f"ACTION:{_escape(alarm.action)}"))
        lines.extend(_fold(f"TRIGGER:{alarm.trigger}"))
        if alarm.description:
            lines.extend(_fold(f"DESCRIPTION:{_escape(alarm.description)}"))
        if alarm.duration:
            lines.extend(_fold(f"DURATION:{alarm.duration}"))
        if alarm.repeat is not None:
            lines.extend(_fold(f"REPEAT:{int(alarm.repeat)}"))
        lines.append("END:VALARM")

    lines.append("END:VEVENT")
    return lines


def _format_event_dt(
    value: datetime | str | None,
    all_day: bool,
    tzinfo: ZoneInfo,
    tzid: str,
) -> tuple[str | None, bool]:
    if value is None:
        if all_day:
            return None, True
        return None, True
    dt = _parse_datetime(value)
    if all_day:
        return _format_date(dt), True
    localized = dt.astimezone(tzinfo)
    if tzid.upper() == "UTC":
        return localized.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ"), True
    return localized.strftime("%Y%m%dT%H%M%S"), False


def _parse_datetime(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
    text = str(value)
    if text.endswith("Z"):
        text = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Invalid ISO timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _format_date(dt: datetime) -> str:
    return dt.date().strftime("%Y%m%d")


def _fold(text: str) -> list[str]:
    if len(text) <= 75:
        return [text]
    output: list[str] = []
    remaining = text
    while len(remaining) > 75:
        chunk = remaining[:75]
        output.append(chunk)
        remaining = " " + remaining[75:]
    output.append(remaining)
    return output


def _escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(";", "\\;")
        .replace(",", "\\,")
    )


def _alarm_to_json(alarm: Alarm) -> dict[str, Any]:
    payload: dict[str, Any] = {"trigger": alarm.trigger, "action": alarm.action}
    if alarm.description is not None:
        payload["description"] = alarm.description
    if alarm.duration is not None:
        payload["duration"] = alarm.duration
    if alarm.repeat is not None:
        payload["repeat"] = alarm.repeat
    return payload


def _to_iso(value: datetime | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.isoformat()
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    return str(value)
