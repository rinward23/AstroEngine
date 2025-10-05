"""Timeline endpoint behavioural tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from astroengine.api_server import app  # noqa: E402


@pytest.fixture(scope="module")
def client() -> TestClient:
    if app is None:
        pytest.skip("FastAPI not available")
    return TestClient(app)


def test_timeline_rejects_outside_swiss_caps(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from astroengine.api.routers import timeline as timeline_router

    stub_settings = SimpleNamespace(
        timeline_ui=True,
        eclipse_finder=True,
        stations=True,
        swiss_caps=SimpleNamespace(min_year=1900, max_year=2100),
    )

    monkeypatch.setattr(timeline_router, "_get_settings", lambda: stub_settings)

    response = client.get(
        "/v1/timeline",
        params={
            "from": "1899-12-31T23:00:00Z",
            "to": "2101-01-01T00:00:00Z",
            "types": "lunations",
        },
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "Swiss Ephemeris coverage" in detail
    assert "Adjust the requested dates" in detail
