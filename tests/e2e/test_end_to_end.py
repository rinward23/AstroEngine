from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from astroengine.api import app

client = TestClient(app)

NATAL = "2000-01-01T00:00:00Z"
START = "2024-01-01T00:00:00Z"
END = "2024-12-31T00:00:00Z"


def _assert_scan(endpoint: str, payload: dict) -> int:
    response = client.post(endpoint, json=payload)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data.get("count"), int)
    assert data["count"] >= 0
    return data["count"]


def test_end_to_end_smoke_suite():
    progression_count = _assert_scan(
        "/v1/scan/progressions",
        {"natal": NATAL, "start": START, "end": END, "step_days": 30.0},
    )
    direction_count = _assert_scan(
        "/v1/scan/directions", {"natal": NATAL, "start": START, "end": END}
    )
    transit_count = _assert_scan(
        "/v1/scan/transits",
        {
            "natal": NATAL,
            "start": START,
            "end": END,
            "bodies": ["Sun", "Mars"],
            "targets": ["Sun", "Mars"],
            "aspects": ["conjunction", "square", "opposition"],
            "orb": 1.5,
            "step_days": 0.5,
        },
    )
    returns_count = _assert_scan(
        "/v1/scan/returns",
        {"natal": NATAL, "start": START, "end": END, "bodies": ["Sun", "Moon"]},
    )

    synastry_response = client.post(
        "/v1/synastry/aspects",
        json={
            "subject": {"ts": NATAL, "lat": 51.5, "lon": -0.12},
            "partner": {"ts": "2001-06-15T12:00:00Z", "lat": 34.05, "lon": -118.25},
            "bodies": ["Sun", "Moon", "Mars"],
        },
    )
    assert synastry_response.status_code == 200
    synastry_data = synastry_response.json()
    assert isinstance(synastry_data.get("count"), int)
    assert synastry_data["count"] >= 0

    assert all(
        count >= 0
        for count in [progression_count, direction_count, transit_count, returns_count]
    )
