"""Shared helpers for transit-oriented CLI commands."""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import asdict, is_dataclass
from typing import Any

from .... import engine as engine_module
from ....utils import (
    DEFAULT_TARGET_FRAMES,
    DEFAULT_TARGET_SELECTION,
    DETECTOR_NAMES,
    ENGINE_FLAG_MAP,
    expand_targets,
)

DEFAULT_MOVING_BODIES: list[str] = ["Sun", "Mars", "Jupiter"]


def normalize_detectors(values: Iterable[str] | None) -> list[str]:
    """Return a normalized, sorted detector selection."""

    if not values:
        return []
    selected: set[str] = set()
    for item in values:
        if not item:
            continue
        raw = str(item)
        for token in raw.replace(",", " ").split():
            key = token.strip().lower()
            if not key:
                continue
            if key == "all":
                return sorted(DETECTOR_NAMES)
            if key in DETECTOR_NAMES:
                selected.add(key)
    return sorted(selected)


def set_engine_detector_flags(detectors: Iterable[str]) -> None:
    """Toggle detector feature flags on the shared engine module."""

    active = {name.lower() for name in detectors}
    for name, attr in ENGINE_FLAG_MAP.items():
        setattr(engine_module, attr, name in active)


def canonical_events_to_dicts(events: Iterable[Any]) -> list[dict[str, Any]]:
    """Convert heterogeneous event objects into plain dictionaries."""

    payload: list[dict[str, Any]] = []
    for event in events:
        if isinstance(event, dict):
            payload.append(dict(event))
            continue
        if is_dataclass(event):
            payload.append(asdict(event))
            continue
        if hasattr(event, "model_dump"):
            try:
                dumped = event.model_dump()
            except Exception:  # pragma: no cover - defensive serialization
                dumped = None
            if isinstance(dumped, dict):
                payload.append(dumped)
                continue
        if hasattr(event, "__dict__"):
            payload.append(dict(vars(event)))
            continue
        payload.append({"value": repr(event)})
    return payload


def _event_summary(event: Any) -> dict[str, Any]:
    if isinstance(event, dict):
        data = event
    elif is_dataclass(event):
        data = asdict(event)
    elif hasattr(event, "model_dump"):
        try:
            dumped = event.model_dump()
        except Exception:  # pragma: no cover - defensive
            dumped = None
        data = dumped if isinstance(dumped, dict) else {}
    elif hasattr(event, "__dict__"):
        data = dict(vars(event))
    else:
        data = {}
    ts = data.get("ts") or data.get("timestamp") or data.get("when_iso")
    moving = data.get("moving") or data.get("body")
    aspect = data.get("aspect") or data.get("kind")
    target = data.get("target") or data.get("natal")
    orb = data.get("orb")
    if orb is None:
        orb = data.get("orb_abs")
    score = data.get("score") or data.get("severity")
    return {
        "ts": ts,
        "moving": moving,
        "aspect": aspect,
        "target": target,
        "orb": orb,
        "score": score,
    }


def format_event_table(events: Iterable[Any]) -> str:
    """Return a human-friendly table summarizing detected events."""

    rows = []
    for event in events:
        summary = _event_summary(event)
        if not summary.get("ts"):
            continue
        rows.append(summary)
    rows.sort(key=lambda item: str(item.get("ts")))
    if not rows:
        return ""
    headers = ["Timestamp", "Moving", "Aspect", "Target", "Orb", "Score"]
    table_rows: list[list[str]] = []
    for row in rows:
        orb = row.get("orb")
        score = row.get("score")
        table_rows.append(
            [
                str(row.get("ts", "")),
                str(row.get("moving", "")),
                str(row.get("aspect", "")),
                str(row.get("target", "")),
                "" if orb is None else f"{float(orb):+0.2f}",
                "" if score is None else f"{float(score):0.2f}",
            ]
        )
    widths = [len(h) for h in headers]
    for row in table_rows:
        for idx, value in enumerate(row):
            widths[idx] = max(widths[idx], len(value))
    header_line = " | ".join(h.ljust(widths[idx]) for idx, h in enumerate(headers))
    divider = "-+-".join("-" * widths[idx] for idx in range(len(headers)))
    body_lines = [
        " | ".join(value.ljust(widths[idx]) for idx, value in enumerate(row))
        for row in table_rows
    ]
    return "\n".join([header_line, divider, *body_lines])


def resolve_targets_cli(
    raw_targets: Iterable[str] | None,
    frames: Iterable[str] | None,
) -> list[str]:
    """Resolve CLI target selections into canonical frame-qualified targets."""

    cleaned = [token.strip() for token in (raw_targets or []) if token]
    if not cleaned:
        return expand_targets(frames or DEFAULT_TARGET_FRAMES, DEFAULT_TARGET_SELECTION)
    return expand_targets(frames or DEFAULT_TARGET_FRAMES, cleaned)


def serialize_events_to_json(events: Sequence[Any]) -> str:
    """Serialize events into a pretty-printed JSON string."""

    return json.dumps(canonical_events_to_dicts(events), indent=2, ensure_ascii=False)


__all__ = [
    "DEFAULT_MOVING_BODIES",
    "canonical_events_to_dicts",
    "format_event_table",
    "normalize_detectors",
    "resolve_targets_cli",
    "serialize_events_to_json",
    "set_engine_detector_flags",
]
