from __future__ import annotations

from fastapi.testclient import TestClient

from astroengine.api import app

client = TestClient(app)


def test_scan_transits_endpoint_returns_hits():
    payload = {
        "natal": "2000-01-01T00:00:00Z",
        "start": "2024-01-01T00:00:00Z",
        "end": "2024-01-15T00:00:00Z",
        "bodies": ["Sun", "Mars"],
        "targets": ["Sun", "Mars"],
        "aspects": ["conjunction", "square", "opposition"],
        "orb": 1.5,
        "step_days": 0.5,
    }
    response = client.post("/v1/scan/transits", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["method"] == "transits"
    assert isinstance(data.get("hits"), list)
    if data["hits"]:
        sample = data["hits"][0]
        assert "aspect" in sample and "orb" in sample


def test_scan_returns_endpoint_includes_return_targets():
    payload = {
        "natal": "2000-01-01T00:00:00Z",
        "start": "2024-01-01T00:00:00Z",
        "end": "2025-01-01T00:00:00Z",
        "bodies": ["Sun", "Moon"],
    }
    response = client.post("/v1/scan/returns", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["method"] == "returns"
    assert isinstance(data.get("hits"), list)
    assert any(hit.get("target") == "Return" for hit in data["hits"])
