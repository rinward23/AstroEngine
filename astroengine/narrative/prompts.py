"""Prompt builders and local fallbacks for narrative summaries."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

__all__ = ["build_summary_prompt", "build_template_summary", "event_to_mapping"]


def event_to_mapping(event: Any) -> Mapping[str, Any]:
    if isinstance(event, Mapping):
        return event
    if hasattr(event, "to_dict"):
        candidate = event.to_dict()
        if isinstance(candidate, Mapping):
            return candidate
    if hasattr(event, "__dict__"):
        return event.__dict__  # type: ignore[return-value]
    raise TypeError(f"Unsupported event type for narrative summary: {type(event)!r}")


def build_summary_prompt(
    events: Sequence[Any],
    *,
    profile: str = "transits",
    timelords: Any | None = None,
    context: Mapping[str, Any] | None = None,
) -> str:
    """Return a chat-friendly prompt describing the supplied events."""

    lines: list[str] = []
    lines.append(
        "You are an astrology interpreter summarizing key events for the reader."
    )
    lines.append(
        "Highlight the themes, note if aspects are tight or wide, and mention relevant planets."
    )
    lines.append(f"Context profile: {profile}.")
    if context:
        context_bits = ", ".join(f"{k}={v}" for k, v in context.items() if v not in (None, ""))
        if context_bits:
            lines.append(f"Profile context: {context_bits}.")
    lines.append("Events:")
    for index, event in enumerate(events, 1):
        payload = event_to_mapping(event)
        timestamp = payload.get("timestamp") or payload.get("ts")
        moving = payload.get("moving") or payload.get("body") or payload.get("transiting_body")
        target = payload.get("target") or payload.get("natal_body")
        kind = payload.get("kind") or payload.get("sign")
        score = payload.get("score")
        orb = payload.get("orb_abs") or payload.get("orb")
        lines.append(
            f"{index}. {timestamp} — {moving} vs {target} ({kind}); score={score} orb={orb}"
        )
    if timelords is not None:
        from .profiles import timelord_outline  # avoid circular import at module level

        outline = timelord_outline(timelords)
        summary = outline.get("summary")
        if summary:
            lines.append(f"Active time-lords: {summary}.")
    lines.append("Compose a concise narrative of 2-3 sentences.")
    return "\n".join(filter(None, lines))


def build_template_summary(
    events: Sequence[Any],
    *,
    title: str = "Top events",
    timelords: Any | None = None,
) -> str:
    """Fallback deterministic formatter when GPT access is unavailable."""

    lines = [title + ":"]
    for event in events:
        payload = event_to_mapping(event)
        timestamp = payload.get("timestamp") or payload.get("ts")
        moving = payload.get("moving") or payload.get("body") or payload.get("transiting_body")
        target = payload.get("target") or payload.get("natal_body") or payload.get("sign")
        kind = payload.get("kind") or payload.get("level")
        score = payload.get("score")
        lines.append(f"- {timestamp}: {moving} → {target} ({kind}), score={score}")
    if timelords is not None:
        from .profiles import timelord_outline

        outline = timelord_outline(timelords)
        if outline.get("summary"):
            lines.append("Time-lords: " + outline["summary"])
    return "\n".join(lines)
