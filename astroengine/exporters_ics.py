"""ICS export helpers for AstroEngine events."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Sequence

from ics.grammar.parse import ContentLine

from .canonical import TransitEvent, event_from_legacy, events_from_any
from .events import ReturnEvent

__all__ = [
    "canonical_events_to_ics",
    "ics_bytes_from_events",
    "write_ics_canonical",
    "DEFAULT_SUMMARY_TEMPLATE",
    "DEFAULT_DESCRIPTION_TEMPLATE",
    "write_ics",
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


DEFAULT_SUMMARY_TEMPLATE = "{label}: {moving} {aspect} {target}"
DEFAULT_DESCRIPTION_TEMPLATE = (
    "Orb {orb:+.2f}° (|{orb_abs:.2f}°|); "
    "Score {score_label}; Profile {profile_id}; Natal {natal_id}"
)


class _TemplateContext(dict):
    def __missing__(self, key: str) -> Any:  # pragma: no cover - formatting fallback
        return ""


def _base_context(ts: str, meta: Mapping[str, Any]) -> Dict[str, Any]:
    natal_id = meta.get("natal_id")
    if natal_id is None and isinstance(meta.get("natal"), Mapping):
        natal_id = meta["natal"].get("id")
    if natal_id is None:
        natal_id = "unknown"
    profile_id = meta.get("profile_id")
    if profile_id is None and isinstance(meta.get("profile"), Mapping):
        profile_id = meta["profile"].get("id")
    return {
        "ts": ts,
        "start": ts,
        "meta": dict(meta),
        "meta_json": json.dumps(meta, sort_keys=True),
        "natal_id": natal_id,
        "profile_id": profile_id,
    }


def _context_from_transit(event: TransitEvent) -> Dict[str, Any]:
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
        label = meta.get("label") or f"{event.moving} ingress {ingress_sign or ctx['target']}"
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


def _context_from_return(event: ReturnEvent) -> Dict[str, Any]:
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
        meta.get("uid")
        or f"{event.ts}-{event.body}-{method}-return",
    )
    return ctx


def _context_from_mapping(payload: Mapping[str, Any]) -> Dict[str, Any]:
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


def _coerce_context(event: Any) -> Dict[str, Any]:
    if isinstance(event, TransitEvent):
        return _context_from_transit(event)
    if isinstance(event, ReturnEvent):
        return _context_from_return(event)
    if isinstance(event, Mapping):
        return _context_from_mapping(event)
    if hasattr(event, "ts") and hasattr(event, "body") and hasattr(event, "method"):
        return _context_from_return(
            ReturnEvent(
                ts=str(getattr(event, "ts")),
                jd=float(getattr(event, "jd", 0.0)),
                body=str(getattr(event, "body")),
                method=str(getattr(event, "method")),
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

    if events is None:
        events = []

    try:
        from ics import Calendar, Event
    except Exception as exc:  # pragma: no cover - optional dependency guard
        raise RuntimeError("The 'ics' package is required for ICS export") from exc

    contexts = [_coerce_context(event) for event in events]
    calendar = Calendar()
    calendar.extra.append(ContentLine("NAME", value=calendar_name))
    calendar.extra.append(ContentLine("X-WR-CALNAME", value=calendar_name))

    count = 0
    for context in contexts:
        evt = Event()
        evt.name = summary_template.format_map(_TemplateContext(context))
        description = description_template.format_map(_TemplateContext(context))
        if description.strip():
            evt.description = description
        evt.begin = context["ts"]
        evt.uid = context.get("uid") or f"{context['ts']}-{count}"
        calendar.events.add(evt)
        count += 1

    Path(path).write_text(str(calendar), encoding="utf-8")
    return count
