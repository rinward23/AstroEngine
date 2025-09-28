"""Utilities for organising interpretation findings into report sections."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Sequence

from jinja2 import Environment

DEFAULT_GROUP = "uncategorized"


@dataclass(slots=True)
class FindingGroup:
    tag: str
    items: List[Dict[str, Any]]


def _primary_tag(finding: Dict[str, Any]) -> str:
    tags = finding.get("tags")
    if isinstance(tags, Sequence) and tags:
        first = tags[0]
        if isinstance(first, str) and first.strip():
            return first.strip()
    return DEFAULT_GROUP


def _score(finding: Dict[str, Any]) -> float:
    value = finding.get("score")
    try:
        return float(value)
    except (TypeError, ValueError):  # pragma: no cover - defensive
        return 0.0


def group_by_primary_tag(findings: Iterable[Dict[str, Any]]) -> List[FindingGroup]:
    """Group findings by their primary tag with deterministic ordering."""

    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for finding in findings:
        tag = _primary_tag(finding)
        buckets.setdefault(tag, []).append(finding)

    groups: List[FindingGroup] = []
    for tag in sorted(buckets.keys(), key=lambda item: item.lower()):
        items = sorted(buckets[tag], key=_score, reverse=True)
        groups.append(FindingGroup(tag=tag, items=items))
    return groups


def render_snippet(finding: Dict[str, Any], env: Environment) -> str | None:
    """Derive a concise snippet for a finding if possible."""

    snippet = finding.get("snippet")
    if isinstance(snippet, str) and snippet.strip():
        return snippet.strip()

    rendered = finding.get("rendered_markdown")
    if isinstance(rendered, str) and rendered.strip():
        first_line = rendered.strip().splitlines()[0].strip()
        return first_line or rendered.strip()

    template_src = finding.get("markdown_template")
    context = finding.get("context", {})
    if not (isinstance(template_src, str) and template_src.strip() and isinstance(context, dict)):
        return None

    try:
        template = env.from_string(template_src)
        rendered = template.render(**context)
    except Exception:  # pragma: no cover - defensive fallback
        return None

    first_line = rendered.strip().splitlines()[0].strip()
    return first_line or rendered.strip() or None


def summarise_scores(totals: Dict[str, Any]) -> Dict[str, float]:
    """Return a flattened mapping of tag → score for table rendering."""

    by_tag = totals.get("by_tag") if isinstance(totals, dict) else None
    result: Dict[str, float] = {}
    if isinstance(by_tag, dict):
        for key, value in by_tag.items():
            try:
                result[str(key)] = float(value)
            except (TypeError, ValueError):  # pragma: no cover - defensive
                continue
    return result
