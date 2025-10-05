"""Report templating helpers for the Streamlit relationship report builder."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from importlib import resources
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Mapping

import pandas as pd

from astroengine.core.dependencies import require_dependency

from . import sections

if TYPE_CHECKING:  # pragma: no cover - import for type checking only
    from jinja2 import Environment as JinjaEnvironment
else:  # pragma: no cover - fallback when jinja2 is absent at runtime
    JinjaEnvironment = Any  # type: ignore[misc,assignment]


TEMPLATE_PACKAGE = "ui.streamlit.report_builder.templates"


@lru_cache(maxsize=1)
def _jinja_primitives():
    """Return the Jinja environment factory and helpers."""

    module = require_dependency(
        "jinja2",
        extras=("narrative", "reports", "streamlit", "ui", "all"),
        purpose="render Streamlit report templates",
    )
    environment = getattr(module, "Environment")
    strict_undefined = getattr(module, "StrictUndefined")
    select_autoescape = getattr(module, "select_autoescape")
    return environment, strict_undefined, select_autoescape


@dataclass(slots=True)
class ReportContext:
    findings: List[Dict[str, Any]]
    rulepack: Mapping[str, Any]
    filters: Mapping[str, Any]
    pair: Mapping[str, Any]
    totals: Mapping[str, Any]
    generated_at: datetime
    top_highlights: int
    template_id: str


def _load_template_source(template_id: str) -> str:
    filename = f"{template_id}.md.j2"
    try:
        return resources.files(TEMPLATE_PACKAGE).joinpath(filename).read_text("utf-8")
    except FileNotFoundError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Unknown template: {template_id}") from exc


def _build_environment() -> JinjaEnvironment:
    environment_cls, strict_undefined_cls, select_autoescape = _jinja_primitives()
    env = environment_cls(autoescape=select_autoescape([]), undefined=strict_undefined_cls)
    env.filters["deg"] = lambda value: f"{float(value):.2f}°"  # type: ignore[arg-type]
    env.filters["round"] = lambda value, ndigits=2: round(float(value), ndigits)  # type: ignore[arg-type]
    return env


def _prepare_findings(ctx: ReportContext, env: JinjaEnvironment) -> List[Dict[str, Any]]:
    prepared: List[Dict[str, Any]] = []
    for finding in ctx.findings:
        snippet = sections.render_snippet(finding, env)
        enriched = dict(finding)
        if snippet:
            enriched["snippet"] = snippet
        prepared.append(enriched)
    prepared.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
    return prepared


def render_markdown(context: ReportContext, *, template_override: str | None = None) -> str:
    """Render a Markdown report from the provided interpretation context."""

    env = _build_environment()
    template_source = template_override or _load_template_source(context.template_id)
    template = env.from_string(template_source)

    findings = _prepare_findings(context, env)
    groups = sections.group_by_primary_tag(findings)
    highlight_count = max(0, int(context.top_highlights))
    highlights = findings[:highlight_count] if highlight_count else []

    appendix = {
        "inputs_link": context.filters.get("inputs_link"),
        "hits_count": len(findings),
        "payload": json.dumps(
            {
                "pair": context.pair,
                "rulepack": context.rulepack,
                "filters": context.filters,
                "totals": context.totals,
            },
            indent=2,
            ensure_ascii=False,
        ),
    }

    scores = {
        "overall": float(context.totals.get("overall", 0.0)),
        "by_tag": sections.summarise_scores(context.totals),
    }

    rendered = template.render(
        pair=context.pair,
        generated_at=context.generated_at.isoformat(timespec="seconds"),
        rulepack=context.rulepack,
        filters=context.filters,
        findings=findings,
        grouped_findings=groups,
        highlights=highlights,
        top_highlights=highlight_count,
        appendix=appendix,
        scores=scores,
    )
    return rendered.strip() + "\n"


def build_scores_table(scores: Mapping[str, float]) -> pd.DataFrame:
    """Create a pandas DataFrame of scores sorted descending."""

    rows = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return pd.DataFrame(rows, columns=["Tag", "Score"])


__all__ = [
    "ReportContext",
    "render_markdown",
    "build_scores_table",
]
