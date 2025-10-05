from __future__ import annotations

import io
import zipfile

import pytest

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from fastapi.testclient import TestClient
pytest.importorskip(
    "pypdf",
    reason="pypdf not installed; install extras with `pip install -e .[reports]`.",
)
from pypdf import PdfReader

from app.routers.reports import router as reports_router

APP = FastAPI(default_response_class=ORJSONResponse)
APP.include_router(reports_router)
CLIENT = TestClient(APP)

META = {
    "title": "Aurora & Vega Relationship Report",
    "subject": "Synastry Highlights",
    "authors": ["AstroEngine"],
    "pair": {"primary": "Aurora", "secondary": "Vega"},
    "keywords": ["synastry", "relationship"],
    "generated_at": "2024-01-10T12:00:00Z",
}

FIGURES = {
    "images": [
        {
            "id": "synastry-wheel",
            "title": "Synastry Wheel",
            "caption": "Composite wheel derived from live charts",
            "media_type": "image/svg+xml",
            "data": "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='40' height='40'%3E%3Ccircle cx='20' cy='20' r='18' stroke='%230055aa' fill='none'/%3E%3C/svg%3E",
        }
    ],
    "tables": [
        {
            "id": "grid",
            "title": "Aspect Grid",
            "headers": ["Body", "Connection"],
            "rows": [["Sun", "Trine Moon"], ["Venus", "Conjunct Mars"]],
        }
    ],
}


def _pdf_payload() -> dict:
    findings = [
        {
            "title": "Sun harmonises Moon",
            "text": "Shared vitality amplifies day-to-day rapport.",
            "score": 4.2,
            "tags": ["support", "warmth"],
        },
        {
            "title": "Mars square Venus",
            "text": "Tension invites deliberate collaboration.",
            "score": 2.8,
            "tags": ["growth"],
        },
    ]
    return {
        "findings": findings,
        "meta": META,
        "theme": "default",
        "figures": FIGURES,
        "include_toc": True,
        "include_appendix": True,
        "paper": "A4",
        "scores": {"harmony": 8.5, "tension": {"Mars-Venus": 3.1}},
    }


def _docx_payload() -> dict:
    markdown = """
# Relationship Synopsis

## Shared Themes
The pair navigates change with curiosity and steadiness.

## Individual Echoes
- Venus emphasises appreciation
- Mars motivates progress
""".strip()
    return {
        "markdown": markdown,
        "meta": {**META, "title": "Aurora & Vega DOCX"},
        "theme": "print",
    }


def test_relationship_pdf_export_from_findings():
    response = CLIENT.post("/v1/report/relationship/pdf", json=_pdf_payload())
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    content = response.content
    assert content.startswith(b"%PDF")
    reader = PdfReader(io.BytesIO(content))
    assert reader.metadata.title == META["title"]
    assert "synastry" in (reader.metadata.keywords or "")


def test_relationship_docx_export_from_markdown():
    response = CLIENT.post("/v1/report/relationship/docx", json=_docx_payload())
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    data = response.content
    assert data.startswith(b"PK")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        core_xml = archive.read("docProps/core.xml").decode("utf-8")
    assert "Aurora &amp; Vega DOCX" in core_xml
