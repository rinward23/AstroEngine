"""Offline narrative templates keyed by AstroEngine profile identifiers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .prompts import event_to_mapping

try:  # pragma: no cover - imported lazily to avoid circular deps
    from astroengine.timelords.models import TimelordStack
except Exception:  # pragma: no cover - Timelord extras optional in tests
    TimelordStack = Any  # type: ignore[assignment]

__all__ = [
    "NarrativeProfileSpec",
    "PROFILE_SPECS",
    "render_profile",
    "timelord_outline",
]


def _format_iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%MZ")
    if isinstance(value, str):
        return value
    return ""


def _coerce_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _event_payload(event: Any) -> dict[str, Any]:
    payload = event_to_mapping(event)
    ts = payload.get("timestamp") or payload.get("ts")
    moving = (
        payload.get("moving") or payload.get("body") or payload.get("transiting_body")
    )
    target = payload.get("target") or payload.get("natal_body") or payload.get("sign")
    aspect = payload.get("aspect") or payload.get("kind") or payload.get("level")
    score = _coerce_float(payload.get("score"))
    orb = _coerce_float(payload.get("orb_abs") or payload.get("orb"))
    confidence = _coerce_float(payload.get("confidence"))
    corridor_info = payload.get("corridor")
    if isinstance(corridor_info, Mapping):
        corridor_width = corridor_info.get("width_deg")
    else:
        corridor_width = payload.get("corridor_width_deg")
    corr = _coerce_float(corridor_width)
    notes = payload.get("notes") or payload.get("summary") or ""
    corridor = corr if isinstance(corr, float) else 0.0
    return {
        "timestamp": _format_iso(ts),
        "moving": str(moving) if moving else "",
        "target": str(target) if target else "",
        "aspect": str(aspect) if aspect else "",
        "score": score,
        "orb": orb,
        "score_text": f"{score:.2f}" if isinstance(score, float) else "n/a",
        "orb_text": f"{orb:.2f}" if isinstance(orb, float) else "—",
        "notes": str(notes) if notes else "",
        "confidence": confidence,
        "corridor_width": corridor,
    }


def _timelord_payload(timelords: Any | None) -> dict[str, Any]:
    base: dict[str, Any] = {
        "lines": [],
        "summary": "",
        "primary": "n/a",
        "primary_ruler": None,
        "systems": [],
    }

    if timelords is None:
        return base

    if isinstance(
        timelords, TimelordStack
    ):  # pragma: no branch - direct access fast path
        periods: Iterable[Any] = timelords.periods
    elif isinstance(timelords, Mapping):
        periods = timelords.get("periods", [])
    else:
        periods = getattr(timelords, "periods", [])

    parsed: list[dict[str, Any]] = []
    for period in periods:
        if hasattr(period, "to_dict"):
            data = period.to_dict()  # type: ignore[assignment]
        elif isinstance(period, Mapping):
            data = dict(period)
        else:  # pragma: no cover - unexpected type
            continue
        parsed.append(data)

    lines: list[str] = []
    for entry in parsed:
        system = str(entry.get("system", "")).replace("_", " ").title()
        level = str(entry.get("level", "")).replace("_", " ")
        ruler = str(entry.get("ruler", ""))
        start = _format_iso(entry.get("start"))
        end = _format_iso(entry.get("end"))
        lines.append(f"{system} {level}: {ruler} ({start} – {end})")

    primary = parsed[0] if parsed else {}
    primary_label = ""
    if primary:
        system = str(primary.get("system", "")).replace("_", " ").title()
        level = str(primary.get("level", ""))
        ruler = str(primary.get("ruler", ""))
        primary_label = f"{system} {level} — {ruler}".strip()

    base.update(
        lines=lines,
        summary="; ".join(lines),
        primary=primary_label or base["primary"],
        primary_ruler=primary.get("ruler"),
        systems=sorted(
            {str(entry.get("system")) for entry in parsed if entry.get("system")}
        ),
    )
    return base


@dataclass(frozen=True)
class NarrativeProfileSpec:
    """Static template metadata for a narrative profile."""

    identifier: str
    title: str
    synopsis: str
    event_template: str
    timelord_template: str | None = None
    closing_template: str | None = None
    tags: Sequence[str] = field(default_factory=tuple)

    def render(
        self,
        events: Sequence[Any],
        *,
        timelords: Any | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> str:
        payloads = [_event_payload(event) for event in events]
        context = context or {}
        lines: list[str] = []
        lines.append(self.title)
        synopsis = self.synopsis.format(count=len(payloads), **context)
        if synopsis:
            lines.append(synopsis)
        for event in payloads:
            line = self.event_template.format(**{**event, **context})
            lines.append(line)
        tl_payload = _timelord_payload(timelords)
        if self.timelord_template and tl_payload.get("lines"):
            lines.append(self.timelord_template.format(**{**tl_payload, **context}))
        if self.closing_template:
            lines.append(self.closing_template.format(**{**tl_payload, **context}))
        return "\n".join(line for line in lines if line).strip()


PROFILE_SPECS: Mapping[str, NarrativeProfileSpec] = {
    "transits": NarrativeProfileSpec(
        identifier="transits",
        title="Transit Highlights",
        synopsis="Top {count} transit hits ranked by AstroEngine scoring.",
        event_template="- {timestamp}: {moving} {aspect} {target} (score {score_text}, orb {orb_text})",
        timelord_template="Active time-lords: {summary}",
        closing_template="Focus on the lead ruler {primary} when prioritising the day.",
        tags=("personal", "transits"),
    ),
    "sidereal": NarrativeProfileSpec(
        identifier="sidereal",
        title="Sidereal Emphasis",
        synopsis="Sidereal channel using {ayanamsha} ayanamsha.",
        event_template="- {timestamp}: {moving} {aspect} {target} — corridor {corridor_width:.2f}°",
        timelord_template="Time-lords guiding the sidereal sequence: {summary}",
        closing_template="Anchor practices around {primary} while ayanamsha remains steady.",
        tags=("sidereal", "ayanamsha"),
    ),
    "mundane": NarrativeProfileSpec(
        identifier="mundane",
        title="Mundane Cycle Watch",
        synopsis="Collective cycles from {count} outer-body hits.",
        event_template="- {timestamp}: {moving} {aspect} {target} (orb {orb_text})",
        timelord_template="Macro periods framing the collective mood: {summary}",
        closing_template="Use these peaks to align mundane timelines with strategic actions.",
        tags=("mundane", "outer_cycles"),
    ),
    "electional": NarrativeProfileSpec(
        identifier="electional",
        title="Electional Windows",
        synopsis="Evaluate {count} shortlisted windows for feasibility.",
        event_template="- {timestamp}: {moving} {aspect} {target} → confidence {confidence:.2f}",
        timelord_template="Underlying time-lords shaping the election: {summary}",
        closing_template="Confirm logistics when the lead timelord {primary} supports the intent.",
        tags=("electional", "planning"),
    ),
    "timelords": NarrativeProfileSpec(
        identifier="timelords",
        title="Active Time-lord Stack",
        synopsis="Stack emphasises {count} concurrent rulers.",
        event_template="- {timestamp}: {moving} {aspect} {target} (score {score_text})",
        timelord_template="Primary rulers: {summary}",
        closing_template="Orient daily actions to the lead {primary} for resonance.",
        tags=("time-lords", "profiles"),
    ),
}


def render_profile(
    profile: str,
    events: Sequence[Any],
    *,
    timelords: Any | None = None,
    context: Mapping[str, Any] | None = None,
) -> str:
    """Render events via the offline template for ``profile``."""

    spec = PROFILE_SPECS.get(profile) or PROFILE_SPECS["transits"]
    return spec.render(events, timelords=timelords, context=context)


def timelord_outline(timelords: Any | None) -> Mapping[str, Any]:
    """Expose the structured timelord payload for external consumers."""

    return _timelord_payload(timelords)
