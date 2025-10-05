from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import engine, session_scope
from app.main import app
from app.repo.charts import ChartRepo

client = TestClient(app)

_SCHEMA_READY = False


def _ensure_schema() -> None:
    global _SCHEMA_READY
    if not _SCHEMA_READY:
        Base.metadata.create_all(bind=engine)
        _SCHEMA_READY = True


def _seed_chart() -> int:
    _ensure_schema()
    with session_scope() as db:
        chart = ChartRepo().create(
            db,
            chart_key=f"chart-{datetime.now(timezone.utc).timestamp()}",
            profile_key="default",
            dt_utc=datetime(2020, 1, 1, tzinfo=timezone.utc),
            lat=0.0,
            lon=0.0,
            data={"kind": "natal"},
        )
        db.flush()
        return chart.id


def test_note_crud_cycle() -> None:
    chart_id = _seed_chart()

    create_resp = client.post(
        "/v1/notes",
        json={"chart_id": chart_id, "text": "First note", "tags": ["progress", "natal"]},
    )
    assert create_resp.status_code == 201
    payload = create_resp.json()
    assert payload["chart_id"] == chart_id
    assert payload["text"] == "First note"
    note_id = payload["id"]

    list_resp = client.get(f"/v1/charts/{chart_id}/notes")
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) == 1
    assert items[0]["id"] == note_id

    delete_resp = client.delete(f"/v1/notes/{note_id}")
    assert delete_resp.status_code == 204

    after_resp = client.get(f"/v1/charts/{chart_id}/notes")
    assert after_resp.status_code == 200
    assert after_resp.json() == []
