from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import engine, session_scope
from app.main import app
from app.repo.charts import ChartRepo
from astroengine.config import default_settings, save_settings

client = TestClient(app)

_SCHEMA_READY = False


def _ensure_schema() -> None:
    global _SCHEMA_READY
    if not _SCHEMA_READY:
        Base.metadata.create_all(bind=engine)
        _SCHEMA_READY = True


def _seed_chart(chart_key: str = "chart-pdf") -> int:
    _ensure_schema()
    with session_scope() as db:
        db.execute(ChartRepo().model.__table__.delete().where(ChartRepo().model.chart_key == chart_key))
        chart = ChartRepo().create(
            db,
            chart_key=chart_key,
            profile_key="pdf",
            dt_utc=datetime(1987, 6, 15, 6, 30, tzinfo=timezone.utc),
            lat=37.7749,
            lon=-122.4194,
            location_name="San Francisco",
            timezone="America/Los_Angeles",
            data={"kind": "natal"},
        )
        db.flush()
        return chart.id


def test_chart_pdf_generation(tmp_path, monkeypatch) -> None:
    pytest.importorskip("swisseph")
    monkeypatch.setenv("ASTROENGINE_HOME", str(tmp_path))
    save_settings(default_settings(), tmp_path / "config.yaml")
    chart_id = _seed_chart()

    response = client.get(f"/v1/charts/{chart_id}/pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_chart_pdf_disabled(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ASTROENGINE_HOME", str(tmp_path))
    settings = default_settings()
    settings.reports.pdf_enabled = False
    save_settings(settings, tmp_path / "config.yaml")
    chart_id = _seed_chart("chart-pdf-disabled")

    response = client.get(f"/v1/charts/{chart_id}/pdf")
    assert response.status_code == 403
