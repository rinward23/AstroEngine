"""Relationship report builder utilities."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from astroengine.exporters.reports.base import (
    FigureBundle,
    HtmlRenderOptions,
    HtmlRenderResult,
    MarginSpec,
    PdfRenderResult,
    ReportMeta,
)
from astroengine.exporters.reports.relationship import context as context_utils
from astroengine.exporters.reports.relationship import docx as docx_renderer
from astroengine.exporters.reports.relationship import markdown as markdown_renderer
from astroengine.exporters.reports.relationship import pdf as pdf_renderer
from astroengine.exporters.reports.relationship import template as template_renderer


@dataclass(slots=True)
class RelationshipReportRequest:
    meta: ReportMeta
    markdown: str | None = None
    findings: Sequence[Mapping[str, Any]] | None = None
    figures: FigureBundle = field(default_factory=FigureBundle)
    theme: str = "default"
    custom_css: str | None = None
    include_toc: bool = True
    include_appendix: bool = True
    paper: str = "A4"
    margins: MarginSpec = field(default_factory=MarginSpec)
    show_header: bool = True
    show_footer: bool = True
    watermark_text: str | None = None
    header_label: str | None = None
    scores: Mapping[str, Any] | None = None
    locale: str = "en"


@dataclass(slots=True)
class RelationshipReportHtml(HtmlRenderResult):
    options: HtmlRenderOptions = field(default_factory=HtmlRenderOptions)


@dataclass(slots=True)
class RelationshipReportBuilder:
    request: RelationshipReportRequest
    _html_cache: RelationshipReportHtml | None = field(default=None, init=False, repr=False)

    def build_html(self) -> RelationshipReportHtml:
        if self._html_cache is not None:
            return self._html_cache
        markdown = self._resolve_markdown()
        body_html, toc_entries = markdown_renderer.markdown_to_html(markdown)
        theme = template_renderer.resolve_theme(self.request.theme, self.request.custom_css)
        options = HtmlRenderOptions(
            paper=self.request.paper,
            include_toc=self.request.include_toc,
            include_appendix=self.request.include_appendix,
            theme=theme,
            margins=self.request.margins,
            show_header=self.request.show_header,
            show_footer=self.request.show_footer,
            watermark_text=self.request.watermark_text,
            custom_css=self.request.custom_css,
            header_label=self.request.header_label
            or context_utils.describe_pair(self.request.meta),
        )
        appendix_tables = context_utils.build_appendix_tables(
            self.request.figures, self.request.scores
        )
        html = template_renderer.render_html(
            markdown_html=body_html,
            toc_entries=toc_entries if self.request.include_toc else [],
            meta=self.request.meta,
            figures=self.request.figures,
            options=options,
            appendix_tables=appendix_tables if self.request.include_appendix else [],
            scores=dict(self.request.scores or {}),
            locale=self.request.locale,
        )
        self._html_cache = RelationshipReportHtml(
            html=html,
            toc_entries=toc_entries,
            markdown=markdown,
            options=options,
        )
        return self._html_cache

    async def render_pdf(self) -> PdfRenderResult:
        html_result = self.build_html()
        return await pdf_renderer.render_pdf(html_result.html, self.request.meta, html_result.options)

    def render_docx(self) -> bytes:
        html_result = self.build_html()
        return docx_renderer.convert_markdown_to_docx(html_result.markdown, self.request.meta)

    def _resolve_markdown(self) -> str:
        if self.request.markdown:
            return self.request.markdown
        if self.request.findings:
            return context_utils.findings_to_markdown(self.request.findings)
        raise ValueError("relationship report requires either markdown or findings data")


class RelationshipReportPdfBuilder(RelationshipReportBuilder):
    async def render(self) -> PdfRenderResult:
        return await self.render_pdf()


class RelationshipReportDocxBuilder(RelationshipReportBuilder):
    def render(self) -> bytes:
        return self.render_docx()
