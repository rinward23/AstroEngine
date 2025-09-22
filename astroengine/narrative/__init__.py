"""Narrative helpers combining templated and GPT-driven summaries."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

try:  # pragma: no cover - optional dependency
    from jinja2 import Template
except Exception:  # pragma: no cover - stub fallback
    Template = None  # type: ignore

from .gpt_api import GPTNarrativeClient
from .prompts import build_summary_prompt, build_template_summary

__all__ = [
    "render_simple",
    "summarize_top_events",
    "build_summary_prompt",
    "build_template_summary",
]

_LOG = logging.getLogger(__name__)

_DEFAULT_TEMPLATE = """
{{ title }}\n\n{% for e in events %}- {{ e }}\n{% endfor %}
"""


def render_simple(title: str, events: Mapping[str, Any]) -> str:
    """Render a simple narrative block using Jinja templates."""

    if Template is None:  # pragma: no cover - guard for optional extra
        raise RuntimeError("Narrative extra not installed. Use: pip install -e .[narrative]")
    return Template(_DEFAULT_TEMPLATE).render(title=title, events=events)


def _event_score(event: Any) -> float:
    candidate: Any
    if isinstance(event, Mapping):
        candidate = event.get("score")
    else:
        candidate = getattr(event, "score", None)
    try:
        return float(candidate)
    except (TypeError, ValueError):
        return 0.0


def summarize_top_events(
    events: Sequence[Any] | Iterable[Any],
    *,
    top_n: int = 5,
    client: GPTNarrativeClient | None = None,
    profile: str = "transits",
) -> str:
    """Return a narrative summary of the top-N events."""

    events_list = list(events)
    if not events_list:
        return "No events available for narrative summary."

    sorted_events = sorted(events_list, key=_event_score, reverse=True)
    top_events = sorted_events[: max(top_n, 1)]

    try:
        prompt = build_summary_prompt(top_events, profile=profile)
    except Exception as exc:  # pragma: no cover - defensive fallback
        _LOG.debug("Failed to build GPT prompt: %s", exc)
        return build_template_summary(top_events)

    client = client or GPTNarrativeClient.from_env()
    if client and client.available:
        try:
            return client.summarize(prompt)
        except Exception as exc:  # pragma: no cover - network or API errors
            _LOG.warning("GPT narrative generation failed; using template fallback: %s", exc)

    return build_template_summary(top_events)
