"""Shared data structures for AstroEngine report exporters."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

BASE_PATH = Path(__file__).resolve().parent


class MarginSpec(BaseModel):
    """Represents margin settings compatible with CSS page boxes."""

    top: str = Field(default="18mm", description="Top margin CSS size value")
    right: str = Field(default="16mm", description="Right margin CSS size value")
    bottom: str = Field(default="20mm", description="Bottom margin CSS size value")
    left: str = Field(default="16mm", description="Left margin CSS size value")


class ReportMeta(BaseModel):
    """Metadata describing the exported document."""

    title: str = Field(..., description="Document title")
    subject: str | None = Field(default=None, description="Document subject line")
    authors: list[str] = Field(default_factory=list, description="Ordered list of authors")
    pair: Mapping[str, str] | None = Field(
        default=None,
        description="Named participants, ex: {'primary': 'Alice', 'secondary': 'Bob'}",
    )
    keywords: list[str] = Field(default_factory=list, description="Keywords embedded in metadata")
    generated_at: datetime = Field(..., description="Timestamp the report was generated")


class FigureAsset(BaseModel):
    """Renderable figure asset for inclusion in reports."""

    id: str = Field(..., description="Identifier for referencing the figure")
    title: str = Field(..., description="Figure title rendered above the figure")
    caption: str | None = Field(default=None, description="Optional caption text")
    media_type: str = Field(..., description="Media type of the payload, e.g. image/svg+xml")
    data: str = Field(
        ..., description="Data URI or base64 encoded payload ready for embedding in HTML"
    )


class TableAsset(BaseModel):
    """Tabular appendix asset."""

    id: str = Field(..., description="Identifier for referencing the table")
    title: str = Field(..., description="Title displayed above the table")
    headers: list[str] = Field(..., description="Column headers")
    rows: list[list[str]] = Field(..., description="Tabular rows of already formatted strings")


class FigureBundle(BaseModel):
    """Collection of optional figures and tables."""

    images: list[FigureAsset] = Field(default_factory=list)
    tables: list[TableAsset] = Field(default_factory=list)


class ThemeOptions(BaseModel):
    """Resolved theme settings including CSS."""

    name: str = Field(default="default")
    css: str = Field(default="", description="Inline CSS payload for the theme")


@dataclass(slots=True)
class HtmlRenderResult:
    """Rendered HTML along with supplemental structures."""

    html: str
    toc_entries: list[dict[str, Any]] = field(default_factory=list)
    markdown: str = ""


@dataclass(slots=True)
class HtmlRenderOptions:
    """Options influencing HTML layout before PDF/DOCX conversion."""

    paper: str = "A4"
    include_toc: bool = True
    include_appendix: bool = True
    theme: ThemeOptions = field(default_factory=ThemeOptions)
    margins: MarginSpec = field(default_factory=MarginSpec)
    show_header: bool = True
    show_footer: bool = True
    watermark_text: str | None = None
    custom_css: str | None = None
    header_label: str | None = None


@dataclass(slots=True)
class PdfRenderResult:
    """Wraps PDF bytes and metadata emitted by the exporters."""

    content: bytes
    renderer: str
    meta: ReportMeta


def iter_authors(meta: ReportMeta) -> Iterable[str]:
    """Utility returning author strings for templating."""

    if not meta.authors:
        return []
    return meta.authors
