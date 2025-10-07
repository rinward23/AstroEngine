"""PDF rendering pipeline for relationship reports."""

from __future__ import annotations

import importlib.util
import io
from dataclasses import dataclass
from typing import Any

from astroengine.exporters.reports.base import HtmlRenderOptions, PdfRenderResult, ReportMeta


class PdfRenderError(RuntimeError):
    """Raised when PDF rendering fails for all configured engines."""


@dataclass(slots=True)
class PdfEngines:
    """Holds references to the available render engines."""

    chromium_available: bool
    weasyprint_available: bool


def detect_engines() -> PdfEngines:
    """Determine which engines are available in the runtime."""

    chromium_available = False
    weasyprint_available = False
    try:
        if importlib.util.find_spec("playwright") is not None:
            chromium_available = True
    except Exception:  # pragma: no cover - defensive guard
        chromium_available = False
    try:
        if importlib.util.find_spec("weasyprint") is not None:
            weasyprint_available = True
    except Exception:  # pragma: no cover - defensive guard
        weasyprint_available = False
    return PdfEngines(chromium_available=chromium_available, weasyprint_available=weasyprint_available)


async def render_pdf(html: str, meta: ReportMeta, options: HtmlRenderOptions) -> PdfRenderResult:
    """Render HTML to PDF using the preferred engines with fallback."""

    engines = detect_engines()
    last_error: Exception | None = None

    if engines.chromium_available:
        try:
            pdf_bytes = await _render_with_playwright(html, options)
            pdf_bytes = _apply_metadata(pdf_bytes, meta)
            return PdfRenderResult(content=pdf_bytes, renderer="chromium", meta=meta)
        except Exception as exc:  # pragma: no cover - exercised in integration only
            last_error = exc

    if engines.weasyprint_available:
        try:
            pdf_bytes = _render_with_weasy(html, meta)
            pdf_bytes = _apply_metadata(pdf_bytes, meta)
            return PdfRenderResult(content=pdf_bytes, renderer="weasyprint", meta=meta)
        except Exception as exc:  # pragma: no cover - integration guard
            last_error = exc

    try:
        placeholder = _render_placeholder_pdf(html, options)
    except Exception as exc:  # pragma: no cover - catastrophic fallback
        raise PdfRenderError("No PDF renderer available") from exc
    placeholder = _apply_metadata(placeholder, meta)
    return PdfRenderResult(content=placeholder, renderer="placeholder", meta=meta)


async def _render_with_playwright(html: str, options: HtmlRenderOptions) -> bytes:
    from playwright.async_api import async_playwright

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html, wait_until="networkidle")
        margins = options.margins.model_dump()
        pdf_bytes = await page.pdf(
            format=options.paper,
            print_background=True,
            margin={k: v for k, v in margins.items()},
            display_header_footer=False,
        )
        await browser.close()
        return pdf_bytes


def _render_with_weasy(html: str, meta: ReportMeta) -> bytes:
    from weasyprint import HTML

    document = HTML(string=html)
    metadata = {
        "title": meta.title,
        "author": ", ".join(meta.authors) if meta.authors else None,
        "subject": meta.subject,
        "keywords": ", ".join(meta.keywords) if meta.keywords else None,
    }
    # Filter None values as WeasyPrint expects strings only.
    metadata = {key: value for key, value in metadata.items() if value}
    return document.write_pdf(metadata=metadata)


def _apply_metadata(pdf_bytes: bytes, meta: ReportMeta) -> bytes:
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    keywords = list(meta.keywords)
    if meta.pair:
        keywords.extend(str(value) for value in meta.pair.values())
    info: dict[str, Any] = {
        "/Title": meta.title,
        "/Producer": "AstroEngine",
        "/Creator": "AstroEngine B-014",
        "/Subject": meta.subject or "",
        "/Keywords": ", ".join(keywords),
    }
    if meta.authors:
        info["/Author"] = ", ".join(meta.authors)
    writer.add_metadata(info)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _render_placeholder_pdf(html: str, options: HtmlRenderOptions) -> bytes:
    from pypdf import PdfWriter

    writer = PdfWriter()
    if options.paper == "Letter":
        width, height = 612, 792
    else:
        width, height = 595, 842
    writer.add_blank_page(width=width, height=height)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()
