"""Narrative composition and summarisation helpers for AstroEngine."""

from __future__ import annotations

import html
import json
import logging
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from ..domains import rollup_domain_scores
from ..infrastructure.paths import profiles_dir
from .gpt_api import GPTNarrativeClient
from .profiles import render_profile, timelord_outline
from .prompts import build_summary_prompt, build_template_summary

try:  # pragma: no cover - optional dependency
    from jinja2 import Template
except Exception:  # pragma: no cover - stub fallback
    Template = None  # type: ignore

__all__ = [
    "NarrativeHighlight",
    "NarrativeCategory",
    "NarrativeDomain",
    "NarrativeTimelord",
    "NarrativeBundle",
    "compose_narrative",
    "render_simple",
    "summarize_top_events",
    "render_profile",
    "timelord_outline",
    "build_summary_prompt",
    "build_template_summary",
    "markdown_to_html",
    "markdown_to_plaintext",
]

_LOG = logging.getLogger(__name__)

_DEFAULT_TEMPLATE = """
{{ title }}\n\n{% for e in events %}- {{ e }}\n{% endfor %}
"""

def _render_simple_template(title: str, events: Mapping[str, Any]) -> str:
    lines = [str(title).strip()]
    for key, value in events.items():
        if isinstance(value, Mapping):
            value_repr = ", ".join(f"{k}={v}" for k, v in value.items())
            lines.append(f"- {key}: {value_repr}")
        else:
            lines.append(f"- {key}: {value}")
    return "\n".join(lines).strip()


@dataclass(frozen=True)
class NarrativeHighlight:
    """Summarised view of a single high-priority event."""

    title: str
    timestamp: str
    category: str
    category_label: str
    summary: str
    score: float
    source: object

    def as_template(self) -> dict[str, str]:
        return {
            "title": self.title,
            "timestamp": self.timestamp,
            "summary": self.summary,
            "score": f"{self.score:.1f}",
        }

    def to_dict(self) -> dict[str, Any]:
        payload = self.as_template()
        payload["category"] = self.category
        payload["category_label"] = self.category_label
        payload["score_raw"] = float(self.score)
        return payload


@dataclass(frozen=True)
class NarrativeCategory:
    """Grouping of highlights sharing a common event category."""

    key: str
    label: str
    score: float
    events: Sequence[NarrativeHighlight]

    def as_template(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "score": f"{self.score:.1f}",
            "events": [event.as_template() for event in self.events],
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.key,
            "label": self.label,
            "score": float(self.score),
            "events": [event.to_dict() for event in self.events],
        }


@dataclass(frozen=True)
class NarrativeDomain:
    """Roll-up of channel activity inside a domain."""

    id: str
    name: str
    score: float
    channels: Sequence[dict[str, Any]]

    def as_template(self) -> dict[str, Any]:
        channel_rows: list[dict[str, str]] = []
        for channel in self.channels:
            score_value = float(channel.get("score", 0.0))
            channel_rows.append(
                {
                    "name": str(channel.get("name", "")),
                    "score": f"{score_value:.1f}",
                }
            )
        return {
            "name": self.name,
            "score": f"{self.score:.1f}",
            "channels": channel_rows,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "score": float(self.score),
            "channels": [
                {
                    **channel,
                    "score": float(channel["score"]),
                    "positive": float(channel.get("positive", 0.0)),
                    "negative": float(channel.get("negative", 0.0)),
                }
                for channel in self.channels
            ],
        }


@dataclass(frozen=True)
class NarrativeTimelord:
    """Summary of an active timelord sequence."""

    name: str
    description: str
    weight: float

    def as_template(self) -> dict[str, str]:
        return {
            "name": self.name,
            "description": self.description,
            "weight": f"{self.weight:.1f}",
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "weight": float(self.weight),
        }


@dataclass(frozen=True)
class NarrativeBundle:
    """Structured narrative result bundle."""

    mode: str
    generated_at: str
    markdown: str
    html: str
    highlights: Sequence[NarrativeHighlight]
    categories: Sequence[NarrativeCategory]
    domains: Sequence[NarrativeDomain]
    timelords: Sequence[NarrativeTimelord]

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "generated_at": self.generated_at,
            "markdown": self.markdown,
            "html": self.html,
            "highlights": [highlight.to_dict() for highlight in self.highlights],
            "categories": [category.to_dict() for category in self.categories],
            "domains": [domain.to_dict() for domain in self.domains],
            "timelords": [timelord.to_dict() for timelord in self.timelords],
        }


_CATEGORY_LABELS = {
    "aspects": "Aspect Contacts",
    "declinations": "Declination Alignments",
    "antiscia": "Mirror Contacts",
    "stations": "Planetary Stations",
    "returns": "Return Windows",
    "progressions": "Progressions",
    "directions": "Directions",
    "timelords": "Timelord Triggers",
    "other": "Additional Highlights",
}


def render_simple(title: str, events: Mapping[str, Any]) -> str:
    """Render a deterministic narrative block with optional templating."""

    if Template is not None:
        return Template(_DEFAULT_TEMPLATE).render(title=title, events=events)
    return _render_simple_template(title, events)


def summarize_top_events(
    events: Sequence[Any] | Iterable[Any],
    *,
    top_n: int = 5,
    client: GPTNarrativeClient | None = None,
    profile: str = "transits",
    timelords: Any | None = None,
    profile_context: Mapping[str, Any] | None = None,
    prefer_template: bool = False,
) -> str:
    """Return a narrative summary of the top-N events."""

    events_list = list(events)
    if not events_list:
        return "No events available for narrative summary."

    sorted_events = sorted(events_list, key=_event_score, reverse=True)
    top_events = sorted_events[: max(top_n, 1)]

    context = dict(profile_context or {})
    offline = render_profile(profile, top_events, timelords=timelords, context=context)

    if prefer_template:
        return offline

    try:
        prompt = build_summary_prompt(
            top_events,
            profile=profile,
            timelords=timelords,
            context=context,
        )
    except Exception as exc:  # pragma: no cover - defensive fallback
        _LOG.debug("Failed to build GPT prompt: %s", exc)
        return offline

    client = client or GPTNarrativeClient.from_env()
    if client and client.available:
        try:
            return client.summarize(prompt)
        except Exception as exc:  # pragma: no cover - network or API errors
            _LOG.warning("GPT narrative generation failed; using template fallback: %s", exc)

    return offline


def compose_narrative(
    events: Sequence[object],
    *,
    mode: str = "template",
    top_n: int = 5,
    generated_at: datetime | str | None = None,
) -> NarrativeBundle:
    """Return a :class:`NarrativeBundle` describing the supplied events."""

    if mode == "llm":
        raise RuntimeError(
            "LLM narrative mode requested but no LLM backend is configured. "
            "Provide a custom composer via astroengine.narrative_llm to enable this mode."
        )
    return _compose_template(events, top_n=top_n, generated_at=generated_at)


def _render_template_markdown(context: Mapping[str, Any]) -> str:
    categories = list(context.get("categories", []))
    domains = list(context.get("domains", []))
    timelords = list(context.get("timelords", []))

    lines: list[str] = []

    def add(line: str) -> None:
        lines.append(line)

    def blank(count: int = 1) -> None:
        if count <= 0:
            return
        lines.extend([""] * count)

    def spacer(count: int = 1) -> None:
        if count <= 0:
            return
        lines.extend(["  "] * count)

    add("# AstroEngine Narrative Summary")
    add(f"Generated at {context['generated_at']}")
    blank(2)

    add("## Event Highlights")
    blank()

    if categories:
        for index, category in enumerate(categories):
            add(f"### {category['label']} (score {category['score']})")
            blank()

            events = list(category.get("events", []))
            if events:
                for event in events:
                    add(
                        "- **{title}** — {summary} ({timestamp}, score {score})".format(
                            title=event["title"],
                            summary=event["summary"],
                            timestamp=event["timestamp"],
                            score=event["score"],
                        )
                    )
                    blank()
            else:
                add("- _No individual highlights available._")
                blank()

            if index != len(categories) - 1:
                blank()
    else:
        add("_No high-score events available for the requested window._")
        blank()

    blank(4)

    add("## Dominant Domains")
    blank()

    if domains:
        for index, domain in enumerate(domains):
            add(f"- {domain['name']} (score {domain['score']})")
            spacer(2)

            channels = list(domain.get("channels") or [])
            if channels:
                for channel in channels:
                    add(
                        "    - {name}: {score}".format(
                            name=channel.get("name", ""),
                            score=channel.get("score", ""),
                        )
                    )
                    spacer()
            else:
                add("    - _No channel activity recorded._")
                spacer()

            spacer()
            if index != len(domains) - 1:
                blank()
    else:
        add("_No domain emphasis detected from the supplied events._")
        blank()

    blank(4)

    add("## Timelord Periods")
    blank()

    if timelords:
        for index, tl in enumerate(timelords):
            add(
                "- {name} — {description} (intensity {weight})".format(
                    name=tl["name"],
                    description=tl["description"],
                    weight=tl["weight"],
                )
            )
            if index != len(timelords) - 1:
                blank()
    else:
        add("_No active timelords were detected for this window._")

    return "\n".join(lines).strip()


def _compose_template(
    events: Sequence[object],
    *,
    top_n: int,
    generated_at: datetime | str | None,
) -> NarrativeBundle:
    highlights = _select_highlights(events, top_n=top_n)
    categories = _build_categories(highlights)
    domains = _summarise_domains(highlights)
    timelords = _summarise_timelords(highlights)
    generated_at_iso = _normalise_generated_at(generated_at)

    context = {
        "generated_at": generated_at_iso,
        "categories": [category.as_template() for category in categories],
        "domains": [domain.as_template() for domain in domains],
        "timelords": [timelord.as_template() for timelord in timelords],
    }

    markdown = _render_template_markdown(context)
    html_output = markdown_to_html(markdown)

    return NarrativeBundle(
        mode="template",
        generated_at=generated_at_iso,
        markdown=markdown,
        html=html_output,
        highlights=highlights,
        categories=categories,
        domains=domains,
        timelords=timelords,
    )


def markdown_to_html(markdown: str) -> str:
    """Very small markdown-to-HTML helper covering headings and lists."""

    lines = markdown.splitlines()
    html_parts: list[str] = []
    in_list = False

    for raw_line in lines:
        line = raw_line.rstrip()
        if not line.strip():
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            continue

        if line.startswith("### "):
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append(f"<h3>{_format_markdown_text(line[4:])}</h3>")
        elif line.startswith("## "):
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append(f"<h2>{_format_markdown_text(line[3:])}</h2>")
        elif line.startswith("# "):
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append(f"<h1>{_format_markdown_text(line[2:])}</h1>")
        elif line.startswith("- "):
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            html_parts.append(f"<li>{_format_markdown_text(line[2:])}</li>")
        else:
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append(f"<p>{_format_markdown_text(line)}</p>")

    if in_list:
        html_parts.append("</ul>")

    return "\n".join(html_parts)


def markdown_to_plaintext(markdown: str) -> str:
    """Collapse markdown into a deterministic plain text block."""

    plain_lines: list[str] = []
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            plain_lines.append("")
            continue
        if line.startswith("#"):
            line = line.lstrip("#").strip()
        elif line.startswith("- "):
            line = f"* {line[2:].strip()}"
        if line.startswith("_") and line.endswith("_") and len(line) > 1:
            line = line[1:-1]
        plain_lines.append(line)
    return "\n".join(plain_lines).strip()


def _format_markdown_text(text: str) -> str:
    content = text.strip()
    italic = content.startswith("_") and content.endswith("_") and len(content) > 1
    if italic:
        content = content[1:-1]
    escaped = html.escape(content, quote=False)
    if italic:
        return f"<em>{escaped}</em>"
    return escaped


def _normalise_generated_at(generated_at: datetime | str | None) -> str:
    if generated_at is None:
        generated = datetime.now(timezone.utc)
    elif isinstance(generated_at, datetime):
        generated = generated_at.astimezone(timezone.utc)
    else:
        return str(generated_at)
    return generated.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _event_attr(event: object, key: str) -> Any:
    if isinstance(event, Mapping):
        return event.get(key)
    return getattr(event, key, None)


def _event_score(event: object) -> float:
    raw = _event_attr(event, "score")
    try:
        return float(raw)
    except (TypeError, ValueError):  # pragma: no cover - defensive
        return 0.0


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


def _select_highlights(events: Sequence[object], *, top_n: int) -> list[NarrativeHighlight]:
    scored: list[tuple[float, str, NarrativeHighlight]] = []
    for event in events:
        score = _event_score(event)
        timestamp = _event_timestamp(event)
        highlight = _make_highlight(event, score=score, timestamp=timestamp)
        scored.append((score, timestamp, highlight))

    scored.sort(key=lambda item: (-item[0], item[1], item[2].title))
    return [entry[2] for entry in scored[: max(top_n, 0)]]


def _make_highlight(event: object, *, score: float, timestamp: str) -> NarrativeHighlight:
    category = _categorise_event(event)
    category_label = _CATEGORY_LABELS.get(category, category.replace("_", " ").title())
    moving = _event_attr(event, "moving")
    target = _event_attr(event, "target")
    kind = _format_kind(_event_attr(event, "kind"))
    parts = [str(part).title() for part in (moving, kind, target) if part]
    title = " ".join(parts) if parts else kind or "Transit Highlight"

    orb_abs = _event_attr(event, "orb_abs")
    orb_allow = _event_attr(event, "orb_allow")
    phase = (_event_attr(event, "applying_or_separating") or "").replace("_", " ").title()
    if orb_abs is not None and orb_allow is not None:
        try:
            orb_text = f"within {float(orb_abs):.2f}° (allow {float(orb_allow):.2f}°)"
        except (TypeError, ValueError):  # pragma: no cover - defensive
            orb_text = "orb metrics unavailable"
    else:
        orb_text = "orb metrics unavailable"
    summary_bits = [orb_text]
    if phase:
        summary_bits.append(phase)
    summary = ", ".join(summary_bits)

    timestamp_value = timestamp or "(undated)"
    return NarrativeHighlight(
        title=title,
        timestamp=timestamp_value,
        category=category,
        category_label=category_label,
        summary=summary,
        score=score,
        source=event,
    )


def _format_kind(kind: Any) -> str:
    if not kind:
        return "Transit"
    text = str(kind)
    if text.startswith("aspect_"):
        return text.split("_", 1)[1].replace("_", " ").title()
    return text.replace("_", " ").title()


def _categorise_event(event: object) -> str:
    kind = str(_event_attr(event, "kind") or "").lower()
    if kind.startswith("aspect_"):
        return "aspects"
    if "decl" in kind:
        return "declinations"
    if "antiscia" in kind:
        return "antiscia"
    if "station" in kind:
        return "stations"
    if "return" in kind:
        return "returns"
    if "progress" in kind:
        return "progressions"
    if "direction" in kind:
        return "directions"
    if "timelord" in kind:
        return "timelords"
    return "other"


def _build_categories(highlights: Sequence[NarrativeHighlight]) -> list[NarrativeCategory]:
    buckets: dict[str, list[NarrativeHighlight]] = defaultdict(list)
    for highlight in highlights:
        buckets[highlight.category].append(highlight)

    categories: list[NarrativeCategory] = []
    for key, items in buckets.items():
        total = sum(item.score for item in items)
        label = _CATEGORY_LABELS.get(key, key.replace("_", " ").title())
        ordered = sorted(items, key=lambda item: (-item.score, item.title))
        categories.append(NarrativeCategory(key=key, label=label, score=total, events=ordered))

    categories.sort(key=lambda category: (-category.score, category.label))
    return categories


@lru_cache(maxsize=1)
def _domain_tree() -> Mapping[str, Any]:
    path = profiles_dir() / "domain_tree.json"
    lines = path.read_text(encoding="utf-8").splitlines()
    payload = "\n".join(line for line in lines if not line.strip().startswith("#"))
    return json.loads(payload) if payload.strip() else {}


def _domain_names() -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    tree = _domain_tree()
    domain_names: dict[str, str] = {}
    channel_names: dict[str, dict[str, str]] = {}
    for domain in tree.get("domains", []):
        domain_id = str(domain.get("id"))
        domain_names[domain_id] = str(domain.get("name", domain_id.title()))
        channel_lookup: dict[str, str] = {}
        for channel in domain.get("channels", []):
            channel_id = str(channel.get("id"))
            channel_lookup[channel_id] = str(channel.get("name", channel_id.title()))
        channel_names[domain_id] = channel_lookup
    return domain_names, channel_names


def _summarise_domains(highlights: Sequence[NarrativeHighlight]) -> list[NarrativeDomain]:
    if not highlights:
        return []
    domain_names, channel_names = _domain_names()
    scores = rollup_domain_scores([highlight.source for highlight in highlights])
    domains: list[NarrativeDomain] = []
    for domain_id, score in scores.items():
        total = float(score.score)
        if abs(total) < 1e-6:
            continue
        channels: list[dict[str, Any]] = []
        for channel_id, channel in score.channels.items():
            net = float(channel.score)
            if abs(net) < 1e-6:
                continue
            positive = channel.sub.get("positive")
            negative = channel.sub.get("negative")
            channels.append(
                {
                    "id": channel_id,
                    "name": channel_names.get(domain_id, {}).get(channel_id, channel_id.title()),
                    "score": net,
                    "positive": float(positive.score) if positive else 0.0,
                    "negative": float(negative.score) if negative else 0.0,
                }
            )
        channels.sort(key=lambda entry: (-entry["score"], entry["name"]))
        domains.append(
            NarrativeDomain(
                id=domain_id,
                name=domain_names.get(domain_id, domain_id.title()),
                score=total,
                channels=channels,
            )
        )
    domains.sort(key=lambda entry: (-entry.score, entry.name))
    return domains


def _summarise_timelords(highlights: Sequence[NarrativeHighlight]) -> list[NarrativeTimelord]:
    buckets: dict[str, dict[str, Any]] = {}
    for highlight in highlights:
        metadata = _event_attr(highlight.source, "metadata")
        if not isinstance(metadata, Mapping):
            continue
        timelord_info = metadata.get("timelord")
        if isinstance(timelord_info, Mapping):
            name = str(timelord_info.get("name") or timelord_info.get("id") or "Timelord")
            description = str(
                timelord_info.get("description")
                or timelord_info.get("period")
                or "Active period"
            )
            weight_raw = timelord_info.get("weight")
            try:
                weight = float(weight_raw) if weight_raw is not None else float(highlight.score)
            except (TypeError, ValueError):  # pragma: no cover - defensive
                weight = float(highlight.score)
        elif isinstance(timelord_info, str):
            name = timelord_info
            description = "Active period"
            weight = float(highlight.score)
        else:
            continue
        key = name.lower()
        bucket = buckets.setdefault(
            key,
            {"name": name, "description": description, "weight": 0.0},
        )
        bucket["weight"] += weight

    timelords = [
        NarrativeTimelord(
            name=data["name"],
            description=data["description"],
            weight=float(data["weight"]),
        )
        for data in buckets.values()
    ]
    timelords.sort(key=lambda entry: (-entry.weight, entry.name))
    return timelords
