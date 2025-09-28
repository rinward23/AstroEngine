"""HTML templating for relationship reports."""

from __future__ import annotations

from functools import lru_cache
from importlib import resources
from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape

from astroengine.exporters.reports.base import (
    FigureBundle,
    HtmlRenderOptions,
    ReportMeta,
    ThemeOptions,
)
from astroengine.exporters.reports.relationship import context as context_utils

PACKAGE_NAME = "astroengine.exporters.reports.relationship"


@lru_cache(maxsize=1)
def _environment() -> Environment:
    env = Environment(
        loader=PackageLoader(PACKAGE_NAME, "templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.globals.update(
        describe_pair=context_utils.describe_pair,
    )
    return env


@lru_cache(maxsize=4)
def _load_css(name: str) -> str:
    path = resources.files(PACKAGE_NAME) / "templates" / "styles" / name
    return path.read_text(encoding="utf-8")


def resolve_theme(theme: str, custom_css: str | None = None) -> ThemeOptions:
    """Combine base styles with the requested theme and optional custom CSS."""

    normalized = theme or "default"
    suffix = normalized.lower()
    theme_filename = f"theme-{suffix}.css"
    base_css = _load_css("base.css")
    try:
        theme_css = _load_css(theme_filename)
    except FileNotFoundError:
        theme_css = _load_css("theme-default.css")
        normalized = "default"
    css_parts = [base_css, theme_css]
    if custom_css:
        css_parts.append(custom_css)
    return ThemeOptions(name=normalized, css="\n\n".join(css_parts))


def render_html(
    *,
    markdown_html: str,
    toc_entries: list[dict[str, Any]],
    meta: ReportMeta,
    figures: FigureBundle,
    options: HtmlRenderOptions,
    appendix_tables: list[Any],
    scores: dict[str, Any] | None = None,
    locale: str = "en",
) -> str:
    """Render the HTML template for the relationship report."""

    template = _environment().get_template("relationship_report.html.j2")
    return template.render(
        body_html=markdown_html,
        toc_entries=toc_entries,
        meta=meta,
        figures=figures,
        options=options,
        appendix_tables=appendix_tables,
        scores=scores or {},
        locale=locale,
    )
