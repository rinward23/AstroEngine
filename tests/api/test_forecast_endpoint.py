from __future__ import annotations

import importlib
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from astroengine.userdata.vault import Natal, save_natal


@pytest.fixture(autouse=True)
def _configure_home(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("ASTROENGINE_HOME", str(tmp_path))
    import astroengine.userdata.vault as vault

    importlib.reload(vault)
    globals()["save_natal"] = vault.save_natal
    globals()["Natal"] = vault.Natal

    import astroengine.api.routers.forecast as forecast_router

    importlib.reload(forecast_router)
    globals()["forecast_router"] = forecast_router


@pytest.fixture()
def client() -> TestClient:
    from astroengine.api import create_app

    app = create_app()
    return TestClient(app)


def _sample_events() -> list[dict[str, Any]]:
    return [
        {
            "start": "2000-01-02T00:00:00Z",
            "end": "2000-01-03T00:00:00Z",
            "body": "Sun",
            "aspect": "conjunction",
            "target": "Moon",
            "exactness": 0.1,
            "technique": "transits",
        },
        {
            "start": "2000-01-04T00:00:00Z",
            "end": "2000-01-05T00:00:00Z",
            "body": "Mars",
            "aspect": "square",
            "target": "Asc",
            "exactness": 0.5,
            "technique": "solar_arc",
        },
    ]


def test_forecast_endpoint_returns_events(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    record = Natal(
        natal_id="sample",
        name=None,
        utc="2000-01-01T12:00:00Z",
        lat=0.0,
        lon=0.0,
    )
    save_natal(record)

    events = _sample_events()
    monkeypatch.setattr(forecast_router, "build_forecast_stack", lambda settings, chart: events)

    response = client.get(
        "/v1/forecast",
        params={
            "natal_id": "sample",
            "from": "2000-01-01T00:00:00Z",
            "to": "2000-01-10T00:00:00Z",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["natal_id"] == "sample"
    assert data["count"] == len(events)
    assert {event["technique"] for event in data["events"]} == {"transits", "solar_arc"}


def test_forecast_endpoint_filters_techniques(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    record = Natal(
        natal_id="filters",
        name=None,
        utc="2001-01-01T12:00:00Z",
        lat=0.0,
        lon=0.0,
    )
    save_natal(record)

    events = _sample_events()
    monkeypatch.setattr(forecast_router, "build_forecast_stack", lambda settings, chart: events)

    response = client.get(
        "/v1/forecast",
        params={
            "natal_id": "filters",
            "from": "2001-01-01T00:00:00Z",
            "to": "2001-01-10T00:00:00Z",
            "techniques": "transits",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["events"][0]["technique"] == "transits"


def test_forecast_endpoint_csv(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    record = Natal(
        natal_id="csv",
        name=None,
        utc="2002-01-01T12:00:00Z",
        lat=0.0,
        lon=0.0,
    )
    save_natal(record)

    events = _sample_events()
    monkeypatch.setattr(forecast_router, "build_forecast_stack", lambda settings, chart: events)

    response = client.get(
        "/v1/forecast",
        params={
            "natal_id": "csv",
            "from": "2002-01-01T00:00:00Z",
            "to": "2002-01-10T00:00:00Z",
            "format": "csv",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    body = response.text.strip().splitlines()
    assert body[0].split(",") == ["start", "end", "body", "aspect", "target", "exactness", "technique"]
    assert len(body) == len(events) + 1


def test_forecast_endpoint_rejects_invalid_window(client: TestClient) -> None:
    record = Natal(
        natal_id="invalid",
        name=None,
        utc="2003-01-01T12:00:00Z",
        lat=0.0,
        lon=0.0,
    )
    save_natal(record)

    response = client.get(
        "/v1/forecast",
        params={
            "natal_id": "invalid",
            "from": "2003-02-01T00:00:00Z",
            "to": "2003-01-01T00:00:00Z",
        },
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "INVALID_WINDOW"
