from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import engine, session_scope
from app.main import app
from app.repo.charts import ChartRepo
from astroengine.atlas.tz import to_utc_with_timezone

client = TestClient(app)

_SCHEMA_READY = False


def _ensure_schema() -> None:
    global _SCHEMA_READY
    if not _SCHEMA_READY:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        _SCHEMA_READY = True


def _clear_charts() -> None:
    _ensure_schema()
    with session_scope() as db:
        repo = ChartRepo()
        db.execute(repo.model.__table__.delete())
        db.flush()


def _seed_charts() -> tuple[int, int]:
    _ensure_schema()
    with session_scope() as db:
        repo = ChartRepo()
        db.execute(repo.model.__table__.delete())
        chart_a = repo.create(
            db,
            chart_key="alpha",
            profile_key="default",
            dt_utc=datetime(2021, 1, 1, 12, 0, tzinfo=UTC),
            lat=0.0,
            lon=0.0,
            data={"kind": "natal"},
        )
        chart_b = repo.create(
            db,
            chart_key="beta",
            profile_key="default",
            dt_utc=datetime(2022, 6, 1, 15, 30, tzinfo=UTC),
            lat=10.0,
            lon=10.0,
            data={"kind": "natal"},
        )
        chart_a.created_at = datetime(2021, 1, 1, tzinfo=UTC)
        chart_b.created_at = datetime(2022, 6, 1, tzinfo=UTC)
        repo.update_tags(db, chart_a.id, ["natal", "client"])
        repo.update_tags(db, chart_b.id, ["progress"])
        db.flush()
        return chart_a.id, chart_b.id


def test_chart_search_and_tags() -> None:
    chart_a, chart_b = _seed_charts()

    response = client.get("/v1/charts", params={"q": "alp"})
    assert response.status_code == 200
    payload = response.json()
    assert any(item["chart_key"] == "alpha" for item in payload)

    tag_response = client.get("/v1/charts", params=[("tag", "natal")])
    assert tag_response.status_code == 200
    tagged = tag_response.json()
    assert tagged and tagged[0]["chart_key"] == "alpha"

    update_response = client.patch(
        f"/v1/charts/{chart_b}/tags", json={"tags": ["Solar", "progress"]}
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["tags"] == ["solar", "progress"]


def test_chart_soft_delete_and_restore() -> None:
    chart_a, _ = _seed_charts()

    delete_resp = client.delete(f"/v1/charts/{chart_a}")
    assert delete_resp.status_code == 204

    deleted_list = client.get("/v1/charts/deleted")
    assert deleted_list.status_code == 200
    deleted_payload = deleted_list.json()
    assert any(item["id"] == chart_a for item in deleted_payload)

    restore_resp = client.post(f"/v1/charts/{chart_a}/restore")
    assert restore_resp.status_code == 200
    restored = restore_resp.json()
    assert restored["deleted_at"] is None


def test_create_chart_stores_timezone_metadata_for_ambiguous_local() -> None:
    pytest.importorskip("swisseph")
    _clear_charts()
    local = datetime(2025, 11, 2, 1, 30)
    resolution = to_utc_with_timezone(local, "America/New_York", ambiguous="latest")
    payload = {
        "name": "DST Ambiguous",
        "kind": "natal",
        "dt_utc": resolution.utc.isoformat().replace("+00:00", "Z"),
        "dt_local": local.isoformat(),
        "tz": "America/New_York",
        "tz_fold": resolution.fold,
        "lat": 40.7128,
        "lon": -74.0060,
    }
    response = client.post("/v1/charts", json=payload)
    assert response.status_code == 201
    data = response.json()
    metadata = data["metadata"].get("timezone_resolution")
    assert metadata is not None
    assert metadata["source"] == "local"
    assert metadata["fold"] == resolution.fold
    assert metadata["ambiguous"] is True
    assert metadata["utc"] == resolution.utc.isoformat().replace("+00:00", "Z")
    assert metadata["tzid"] in {"America/New_York", "US/Eastern"}


def test_create_chart_stores_timezone_metadata_for_nonexistent_local() -> None:
    pytest.importorskip("swisseph")
    _clear_charts()
    local = datetime(2025, 3, 9, 2, 30)
    resolution = to_utc_with_timezone(local, "America/New_York", nonexistent="post")
    payload = {
        "name": "DST Gap",
        "kind": "natal",
        "dt_utc": resolution.utc.isoformat().replace("+00:00", "Z"),
        "dt_local": local.isoformat(),
        "tz": "America/New_York",
        "tz_fold": resolution.fold,
        "lat": 40.7128,
        "lon": -74.0060,
    }
    response = client.post("/v1/charts", json=payload)
    assert response.status_code == 201
    data = response.json()
    metadata = data["metadata"].get("timezone_resolution")
    assert metadata is not None
    assert metadata["source"] == "local"
    assert metadata["nonexistent"] is True
    assert metadata["gap_seconds"] == 3600
    assert metadata["utc"] == resolution.utc.isoformat().replace("+00:00", "Z")
