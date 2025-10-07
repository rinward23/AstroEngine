"""Markdown helpers for relationship reports."""

from __future__ import annotations

import re
from collections.abc import Iterable
from functools import lru_cache
from typing import Any

from markdown_it import MarkdownIt
from markdown_it.token import Token
from mdit_py_plugins.attrs import attrs_plugin
from mdit_py_plugins.footnote import footnote_plugin

HEADING_PATTERN = re.compile(r"[^a-z0-9]+")


@lru_cache(maxsize=1)
def _markdown_parser() -> MarkdownIt:
    md = MarkdownIt("commonmark", {"html": True, "linkify": True})
    md.enable("table")
    md.enable("strikethrough")
    md.use(footnote_plugin)
    md.use(attrs_plugin)
    return md


def _slugify(text: str) -> str:
    slug = HEADING_PATTERN.sub("-", text.lower()).strip("-")
    return slug or "section"


def _heading_text(token: Token) -> str:
    if token is None:
        return ""
    if token.type != "inline" or not token.children:
        return token.content
    return "".join(child.content for child in token.children if hasattr(child, "content"))


def markdown_to_html(markdown: str, include_levels: Iterable[int] = (2, 3, 4)) -> tuple[str, list[dict[str, Any]]]:
    """Render Markdown to HTML while collecting heading metadata."""

    md = _markdown_parser()
    tokens = md.parse(markdown)
    toc_entries: list[dict[str, Any]] = []

    for idx, token in enumerate(tokens):
        if token.type != "heading_open":
            continue
        level = int(token.tag[1])
        if include_levels and level not in include_levels:
            continue
        next_token = tokens[idx + 1] if idx + 1 < len(tokens) else None
        title = _heading_text(next_token) if next_token else ""
        slug = _slugify(title)
        token.attrSet("id", slug)
        if next_token is not None and next_token.map is not None:
            next_token.attrSet("id", slug)
        toc_entries.append({"level": level, "title": title, "slug": slug})

    html = md.renderer.render(tokens, md.options, {})
    return html, toc_entries
