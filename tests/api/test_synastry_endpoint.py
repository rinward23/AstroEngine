"""API integration tests for the synastry router."""

from __future__ import annotations

import pytest

try:  # pragma: no cover - optional dependency in test environment
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover - FastAPI not installed
    TestClient = None  # type: ignore[assignment]

from astroengine.api_server import app

pytestmark = pytest.mark.skipif(
    app is None or TestClient is None, reason="FastAPI not available"
)


def test_synastry_aspects_endpoint_shape() -> None:
    client = TestClient(app)  # type: ignore[misc]
    payload = {
        "a": {"ts": "1995-05-15T14:00:00Z", "lat": 37.7749, "lon": -122.4194},
        "b": {"ts": "1988-11-02T06:45:00Z", "lat": 48.8566, "lon": 2.3522},
    }
    response = client.post("/v1/synastry/aspects", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"count", "summary", "hits"}
    assert isinstance(data["count"], int)
    assert isinstance(data["summary"], dict)
    assert isinstance(data["hits"], list)
    if data["hits"]:
        first = data["hits"][0]
        assert {"direction", "moving", "target", "aspect", "orb"}.issubset(first)
    client.close()
