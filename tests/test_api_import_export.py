from __future__ import annotations

import io
import json
import zipfile
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.base import Base
from app.db.models import Chart
from app.db.session import engine, session_scope
from app.main import app
from app.repo.charts import ChartRepo
from astroengine.config import default_settings, load_settings, save_settings

client = TestClient(app)

_SCHEMA_READY = False


def _ensure_schema() -> None:
    global _SCHEMA_READY
    if not _SCHEMA_READY:
        Base.metadata.create_all(bind=engine)
        _SCHEMA_READY = True


def _configure_settings_home(tmp_path) -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    save_settings(default_settings(), tmp_path / "config.yaml")


def _seed_chart(chart_key: str = "chart-export") -> int:
    _ensure_schema()
    with session_scope() as db:
        db.execute(ChartRepo().model.__table__.delete().where(ChartRepo().model.chart_key == chart_key))
        chart = ChartRepo().create(
            db,
            chart_key=chart_key,
            profile_key="exporter",
            dt_utc=datetime(2021, 3, 21, 12, 0, tzinfo=UTC),
            lat=51.5074,
            lon=-0.1278,
            location_name="London",
            timezone="Europe/London",
            data={"kind": "natal"},
        )
        db.flush()
        return chart.id


def test_export_bundle_contains_requested_scopes(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ASTROENGINE_HOME", str(tmp_path))
    _configure_settings_home(tmp_path)
    _seed_chart()

    response = client.get("/v1/export", params={"scope": "charts,settings"})
    assert response.status_code == 200
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    try:
        charts_payload = json.loads(archive.read("charts.json"))
        assert any(item.get("chart_key") == "chart-export" for item in charts_payload)
        settings_payload = json.loads(archive.read("settings.json"))
        assert settings_payload["reports"]["pdf_enabled"] is True
    finally:
        archive.close()


def test_import_bundle_upserts_charts(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ASTROENGINE_HOME", str(tmp_path))
    _configure_settings_home(tmp_path)

    with session_scope() as db:
        ChartRepo().create(
            db,
            chart_key="imported-chart",
            profile_key="import",
            kind="natal",
            dt_utc=datetime(2019, 1, 1, 0, 0, tzinfo=UTC),
            lat=0.0,
            lon=0.0,
            location_name="Initial",
            timezone="UTC",
            data={"kind": "natal"},
        )

    bundle_buffer = io.BytesIO()
    with zipfile.ZipFile(bundle_buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "settings.json",
            json.dumps(
                {
                    **default_settings().model_dump(),
                    "reports": {"pdf_enabled": False, "disclaimers": ["Imported"]},
                },
                indent=2,
            ),
        )
        archive.writestr(
            "charts.json",
            json.dumps(
                [
                    {
                        "chart_key": "imported-chart",
                        "profile_key": "import",
                        "kind": "natal",
                        "dt_utc": "2020-05-10T08:30:00+00:00",
                        "lat": 34.0522,
                        "lon": -118.2437,
                        "location_name": "Los Angeles",
                        "timezone": "America/Los_Angeles",
                        "name": "Updated Import",
                        "data": {"kind": "natal"},
                    },
                    {
                        "chart_key": "second-chart",
                        "profile_key": "import",
                        "kind": "event",
                        "dt_utc": "2023-01-01T12:00:00+00:00",
                        "lat": 40.7128,
                        "lon": -74.006,
                        "location_name": "New York",
                        "timezone": "America/New_York",
                        "data": {"kind": "event"},
                    },
                ],
                indent=2,
            ),
        )
    bundle_buffer.seek(0)

    response = client.post(
        "/v1/import",
        files={"bundle": ("bundle.zip", bundle_buffer.getvalue(), "application/zip")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["charts_processed"] == 2
    assert payload["charts_created"] == 1
    assert payload["charts_updated"] == 1
    assert payload["settings_applied"] is True

    with session_scope() as db:
        chart = (
            db.execute(select(Chart).where(Chart.chart_key == "imported-chart"))
            .scalar_one_or_none()
        )
        assert chart is not None
        assert chart.location_name == "Los Angeles"
        assert chart.timezone == "America/Los_Angeles"
        assert chart.name == "Updated Import"
        second = (
            db.execute(select(Chart).where(Chart.chart_key == "second-chart"))
            .scalar_one_or_none()
        )
        assert second is not None
        assert second.location_name == "New York"

    settings = load_settings(tmp_path / "config.yaml")
    assert settings.reports.pdf_enabled is False
    assert settings.reports.disclaimers == ["Imported"]
