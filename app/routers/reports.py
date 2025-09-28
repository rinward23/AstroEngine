from __future__ import annotations

import requests
from fastapi import APIRouter, HTTPException, Response

from app.schemas.reports import (
    RelationshipReportDocxRequest,
    RelationshipReportPdfRequest,
)
from astroengine.exporters.reports.relationship import (
    RelationshipReportDocxBuilder,
    RelationshipReportPdfBuilder,
    RelationshipReportRequest,
)
from astroengine.exporters.reports.relationship.docx import DocxUnavailable
from astroengine.exporters.reports.relationship.pdf import PdfRenderError

router = APIRouter(prefix="/v1/report/relationship", tags=["Relationship Reports"])

MAX_CSS_BYTES = 256_000


def _to_builder_request(model: RelationshipReportPdfRequest | RelationshipReportDocxRequest) -> RelationshipReportRequest:
    custom_css = None
    if model.custom_theme_url:
        custom_css = _load_custom_css(str(model.custom_theme_url))
    return RelationshipReportRequest(
        meta=model.meta,
        markdown=model.markdown,
        findings=model.findings,
        figures=model.figures,
        theme=model.theme,
        custom_css=custom_css,
        include_toc=model.include_toc,
        include_appendix=model.include_appendix,
        paper=model.paper,
        margins=model.margins,
        show_header=model.show_header,
        show_footer=model.show_footer,
        watermark_text=model.watermark_text,
        header_label=model.header_label,
        scores=model.scores,
        locale=model.locale,
    )


def _load_custom_css(url: str) -> str:
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
    except Exception as exc:  # pragma: no cover - network failure
        raise HTTPException(status_code=400, detail="Failed to download custom theme CSS") from exc
    if len(response.content) > MAX_CSS_BYTES:
        raise HTTPException(status_code=400, detail="Custom theme CSS exceeds size limit")
    content_type = response.headers.get("Content-Type", "text/plain")
    if "css" not in content_type and "text" not in content_type:
        raise HTTPException(status_code=400, detail="Custom theme content type not supported")
    return response.text


@router.post("/pdf")
async def relationship_report_pdf(req: RelationshipReportPdfRequest) -> Response:
    builder = RelationshipReportPdfBuilder(_to_builder_request(req))
    try:
        result = await builder.render()
    except PdfRenderError as exc:
        raise HTTPException(status_code=503, detail="PDF rendering unavailable") from exc
    headers = {
        "Content-Disposition": 'attachment; filename="relationship_report.pdf"',
    }
    return Response(content=result.content, media_type="application/pdf", headers=headers)


@router.post("/docx")
async def relationship_report_docx(req: RelationshipReportDocxRequest) -> Response:
    builder = RelationshipReportDocxBuilder(_to_builder_request(req))
    try:
        docx_bytes = builder.render()
    except DocxUnavailable as exc:
        raise HTTPException(status_code=503, detail="DOCX rendering unavailable") from exc
    headers = {
        "Content-Disposition": 'attachment; filename="relationship_report.docx"',
    }
    media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return Response(content=docx_bytes, media_type=media_type, headers=headers)


__all__ = ["router"]
