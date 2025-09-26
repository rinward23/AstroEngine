"""Minimal iCalendar export helpers for scan hits."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from icalendar import Calendar, Event

__all__ = ["write_ics"]


def _ensure_datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise ValueError(f"Invalid ISO timestamp for ICS export: {value!r}") from exc


def _get(source: Any, key: str) -> Any:
    if isinstance(source, Mapping):
        return source.get(key)
    return getattr(source, key, None)


def write_ics(path: str | Path, hits: Iterable[Any]) -> Path:
    """Write ``hits`` into an iCalendar file located at ``path``.

    Parameters
    ----------
    path:
        Destination filesystem location. Parent directories are created on
        demand.
    hits:
        Iterable of objects or mappings exposing the ``when_iso``, ``moving``,
        ``target`` and ``aspect`` attributes.
    """

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    calendar = Calendar()
    calendar.add("prodid", "-//AstroEngine//Scan Hits//EN")
    calendar.add("version", "2.0")

    for hit in hits:
        when_iso = _get(hit, "when_iso")
        moving = _get(hit, "moving")
        target = _get(hit, "target")
        aspect = _get(hit, "aspect")
        if when_iso is None or moving is None or target is None or aspect is None:
            continue
        event = Event()
        event.add("dtstart", _ensure_datetime(str(when_iso)))
        summary = f"{moving} {aspect} {target}"
        event.add("summary", summary)
        calendar.add_component(event)

    destination.write_bytes(calendar.to_ical())
    return destination
