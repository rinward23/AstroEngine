"""ICS export helpers for canonical, templated, and narrative event exports."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .canonical import TransitEvent, event_from_legacy, events_from_any
from .events import ReturnEvent
from .narrative import markdown_to_plaintext

DEFAULT_SUMMARY_TEMPLATE = "{label}: {moving} {aspect} {target}"
DEFAULT_DESCRIPTION_TEMPLATE = (
    "Orb {orb:+.2f}° (|{orb_abs:.2f}°|); "
    "Score {score_label}; Profile {profile_id}; Natal {natal_id}"
)


__all__ = [
    "DEFAULT_DESCRIPTION_TEMPLATE",
    "DEFAULT_SUMMARY_TEMPLATE",
    "canonical_events_to_ics",
    "ics_bytes_from_events",
    "write_ics_canonical",
    "write_ics",
    "format_ics_calendar",
    "write_ics_calendar",
]

_PRODID = "-//AstroEngine//Transit Scanner//EN"
_NARRATIVE_PRODID = "-//AstroEngine//Narrative Calendar 1.0//EN"


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

    moment = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(UTC)
    return moment.strftime("%Y%m%dT%H%M%SZ")


def _render_calendar(events: Sequence[TransitEvent], calendar_name: str) -> str:
    now_stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
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

        uid_source = (
            f"{dt_start}|{summary}|{event.orb}|{event.score}|{event.meta!r}".encode()
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


class _TemplateContext(dict):
    def __missing__(self, key: str) -> Any:  # pragma: no cover - formatting fallback
        return ""


def _base_context(ts: str, meta: Mapping[str, Any]) -> dict[str, Any]:

    natal_id = meta.get("natal_id")
    if natal_id is None and isinstance(meta.get("natal"), Mapping):
        natal_id = meta["natal"].get("id")
    profile_id = meta.get("profile_id")
    if profile_id is None and isinstance(meta.get("profile"), Mapping):
        profile_id = meta["profile"].get("id")

    return {
        "ts": ts,
        "start": ts,
        "meta": dict(meta),
        "meta_json": json.dumps(meta, sort_keys=True),
        "natal_id": natal_id or "unknown",
        "profile_id": profile_id or "unknown",
    }


def _context_from_transit(event: TransitEvent) -> dict[str, Any]:

    meta = dict(event.meta or {})
    ctx = _base_context(event.ts, meta)
    ctx.update(
        moving=event.moving,
        target=meta.get("ingress_target") or event.target,
        aspect=event.aspect,
        orb=float(event.orb),
        orb_abs=float(abs(event.orb)),
        applying=bool(event.applying),
        score=0.0 if event.score is None else float(event.score),
        score_label="" if event.score is None else f"{float(event.score):.2f}",
    )
    ingress_sign = (
        meta.get("ingress_sign")
        or meta.get("sign")
        or meta.get("zodiac_sign")
        or meta.get("ingress_target")
    )
    kind_raw = (
        meta.get("event_type")
        or meta.get("category")
        or meta.get("kind")
        or ("ingress" if meta.get("ingress") else None)
        or "transit"
    )
    kind = str(kind_raw).lower()
    if kind == "ingress":
        label = (
            meta.get("label")
            or f"{event.moving} ingress {ingress_sign or ctx['target']}"
        )
    else:
        label = meta.get("label") or f"{event.moving} {event.aspect} {event.target}"
    ctx.update(
        type=kind,
        label=label,
        ingress_sign=ingress_sign,
    )
    ctx.setdefault(
        "uid",
        meta.get("uid")
        or f"{event.ts}-{event.moving}-{ctx['target']}-{kind}-{abs(hash(json.dumps(meta, sort_keys=True)))%10_000}",
    )
    return ctx


def _context_from_return(event: ReturnEvent) -> dict[str, Any]:

    meta = dict(getattr(event, "meta", {}) or {})
    ctx = _base_context(event.ts, meta)
    method = getattr(event, "method", "return")
    label = meta.get("label") or f"{event.body} {method.title()} return"
    ctx.update(
        moving=event.body,
        target=f"{method.lower()} return",
        aspect="return",
        orb=0.0,
        orb_abs=0.0,
        applying=False,
        score=0.0,
        score_label="",
        label=label,
        type="return",
        longitude=getattr(event, "longitude", None),
        jd=getattr(event, "jd", None),
    )
    ctx.setdefault(
        "uid",
        meta.get("uid") or f"{event.ts}-{event.body}-{method}-return",
    )
    return ctx


def _context_from_mapping(payload: Mapping[str, Any]) -> dict[str, Any]:

    kind = (payload.get("type") or payload.get("event_type") or "").lower()
    if kind == "return":
        ts_val = payload.get("ts") or payload.get("timestamp")
        if ts_val is None:
            raise ValueError("Return events require a 'ts' timestamp for ICS export")
        body_val = payload.get("body") or payload.get("moving")
        if body_val is None:
            raise ValueError("Return events require a 'body' identifier")
        return _context_from_return(
            ReturnEvent(
                ts=str(ts_val),
                jd=float(payload.get("jd", 0.0)),
                body=str(body_val),
                method=str(payload.get("method", payload.get("kind", "return"))),
                longitude=float(payload.get("longitude", 0.0)),
            )
        )
    return _context_from_transit(event_from_legacy(payload))


def _coerce_context(event: Any) -> dict[str, Any]:

    if isinstance(event, TransitEvent):
        return _context_from_transit(event)
    if isinstance(event, ReturnEvent):
        return _context_from_return(event)
    if isinstance(event, Mapping):
        return _context_from_mapping(event)
    if hasattr(event, "ts") and hasattr(event, "body") and hasattr(event, "method"):
        return _context_from_return(
            ReturnEvent(
                ts=str(event.ts),
                jd=float(getattr(event, "jd", 0.0)),
                body=str(event.body),
                method=str(event.method),
                longitude=float(getattr(event, "longitude", 0.0)),
            )
        )
    return _context_from_transit(event_from_legacy(event))


def write_ics(
    path: str | Path,
    events: Iterable[Any],
    *,
    calendar_name: str = "AstroEngine Events",
    summary_template: str = DEFAULT_SUMMARY_TEMPLATE,
    description_template: str = DEFAULT_DESCRIPTION_TEMPLATE,
) -> int:
    """Write events to an ICS file using summary/description templates."""

    contexts = [_coerce_context(event) for event in events]
    now_stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{_PRODID}",
        f"NAME:{_escape_text(calendar_name)}",
        f"X-WR-CALNAME:{_escape_text(calendar_name)}",
    ]

    for context in contexts:
        dtstart = _iso_to_ics(context["ts"])
        dtend = _iso_to_ics(context["ts"], delta_minutes=30)
        summary = summary_template.format_map(_TemplateContext(context)).strip()
        description = description_template.format_map(_TemplateContext(context)).strip()
        uid_value = context.get("uid")
        if not uid_value:
            raw = f"{dtstart}|{summary}|{description}|{context.get('type','')}".encode()
            uid_value = hashlib.sha1(raw).hexdigest()

        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uid_value}@astroengine",
                f"DTSTAMP:{now_stamp}",
                f"DTSTART:{dtstart}",
                f"DTEND:{dtend}",
                f"SUMMARY:{_escape_text(summary)}",
            ]
        )
        if description:
            lines.append(f"DESCRIPTION:{_escape_text(description)}")
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    Path(path).write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    return len(contexts)


def write_ics_calendar(
    path: str | Path,
    events: Iterable[object],
    *,
    title: str,
    narrative_text: object | None = None,
) -> int:
    """Write an ICS file including the optional narrative summary block."""

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
    """Return an ICS calendar as a string with folded narrative descriptions."""

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
        f"PRODID:{_NARRATIVE_PRODID}",
        f"X-WR-CALNAME:{_escape_text(str(title))}",
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
                *_fold_ics_line(f"SUMMARY:{_escape_text(summary)}"),
            ]
        )
        if description:
            lines.extend(_fold_ics_line(f"DESCRIPTION:{_escape_text(description)}"))
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def _prepare_narrative_block(narrative: object | None) -> str | None:
    if narrative is None:
        return None
    if hasattr(narrative, "markdown"):
        markdown = narrative.markdown
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
        return datetime(1970, 1, 1, tzinfo=UTC)
    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:  # pragma: no cover - defensive
        return datetime(1970, 1, 1, tzinfo=UTC)


def _iso_to_ics(timestamp: str, *, delta_minutes: int = 0) -> str:
    if timestamp:
        try:
            base = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(
                UTC
            )
        except ValueError:  # pragma: no cover - defensive
            base = datetime(1970, 1, 1, tzinfo=UTC)
    else:
        base = datetime(1970, 1, 1, tzinfo=UTC)
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
