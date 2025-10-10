from __future__ import annotations

import io
import json
import zipfile
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.routers.data_io as data_io
from app.db.base import Base
from app.db.session import engine, session_scope
from app.repo.charts import ChartRepo


@pytest.fixture()
def export_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("ASTROENGINE_HOME", str(tmp_path))
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    test_app = FastAPI()
    test_app.include_router(data_io.router)
    return TestClient(test_app)


def test_export_many_charts_streams_without_list(export_client, monkeypatch) -> None:
    repo = ChartRepo()
    with session_scope() as db:
        for index in range(250):
            repo.create(
                db,
                chart_key=f"bulk-{index}",
                profile_key="export",
                dt_utc=datetime(2021, 1, 1, 12, tzinfo=UTC),
                lat=10.0 + index,
                lon=20.0 + index,
                location_name=f"Location {index}",
                timezone="UTC",
                data={"index": index},
            )
        db.flush()

    original_dumps = data_io.json.dumps

    def guarded_dumps(obj, *args, **kwargs):  # type: ignore[override]
        if isinstance(obj, list):
            raise AssertionError("charts export should not serialise full list at once")
        return original_dumps(obj, *args, **kwargs)

    monkeypatch.setattr(data_io.json, "dumps", guarded_dumps)

    response = export_client.get("/v1/export", params={"scope": "charts"})
    assert response.status_code == 200, response.text

    archive = zipfile.ZipFile(io.BytesIO(response.content))
    try:
        charts_raw = archive.read("charts.json").decode("utf-8")
    finally:
        archive.close()

    assert charts_raw.startswith("["), charts_raw[:32]
    payload = json.loads(charts_raw)
    assert len(payload) == 250
    assert payload[0]["chart_key"].startswith("bulk-0")
