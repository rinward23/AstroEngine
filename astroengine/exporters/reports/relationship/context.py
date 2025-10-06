"""Context assembly for relationship reports."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from astroengine.exporters.reports.base import FigureBundle, ReportMeta, TableAsset


@dataclass(slots=True)
class AppendixData:
    """Appendix payload derived from findings and supplemental assets."""

    tables: list[TableAsset]
    figures: FigureBundle


def findings_to_markdown(findings: Sequence[Mapping[str, Any]]) -> str:
    """Render findings returned by the interpretation engine to Markdown.

    Each finding is expected to provide ``title`` and ``text`` keys. Optional ``score``
    and ``tags`` entries are embedded when available. The resulting Markdown keeps the
    hierarchy predictable for the downstream HTML renderer.
    """

    lines: list[str] = []
    if not findings:
        return ""
    lines.append("## Highlights")
    for idx, item in enumerate(findings, 1):
        title = item.get("title") or f"Finding {idx}"
        score = item.get("score")
        header = f"### {idx}. {title}" if not title.startswith("#") else title
        lines.append(header)
        if score is not None:
            lines.append(f"**Score:** {score:.2f}")
        tags = item.get("tags") or []
        if tags:
            tags_line = ", ".join(str(tag) for tag in tags)
            lines.append(f"**Tags:** {tags_line}")
        text = item.get("text") or ""
        lines.append(text.strip())
        lines.append("")
    return "\n".join(lines).strip()


def build_appendix_tables(figures: FigureBundle, scores: Mapping[str, Any] | None = None) -> list[TableAsset]:
    """Construct appendix tables from provided score/grid data.

    ``scores`` may contain numeric or string payloads. Values are rendered as strings to
    preserve fidelity.
    """

    tables = list(figures.tables)
    if not scores:
        return tables

    rows: list[list[str]] = []
    for key, value in scores.items():
        if isinstance(value, Mapping):
            for inner_key, inner_val in value.items():
                rows.append([f"{key}:{inner_key}", str(inner_val)])
        else:
            rows.append([str(key), str(value)])
    tables.append(
        TableAsset(
            id="scores",
            title="Scores Overview",
            headers=["Metric", "Value"],
            rows=rows,
        )
    )
    return tables


def describe_pair(meta: ReportMeta) -> str:
    """Return a human readable description for the pair displayed on the cover."""

    if not meta.pair:
        return ""
    primary = meta.pair.get("primary") or meta.pair.get("a")
    secondary = meta.pair.get("secondary") or meta.pair.get("b")
    if primary and secondary:
        return f"{primary} × {secondary}"
    return ", ".join(str(value) for value in meta.pair.values())
