from __future__ import annotations

import json
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from astroengine.api_server import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    if app is None:
        pytest.skip("FastAPI not available")
    return TestClient(app)


def _base_payload(method: str) -> dict:
    return {
        "method": method,
        "natal_inline": {
            "ts": "2000-01-01T00:00:00Z",
            "lat": 51.5,
            "lon": -0.1,
        },
        "from": "2024-01-01T00:00:00Z",
        "to": "2024-12-31T00:00:00Z",
    }


def test_scan_progressions_endpoint(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _base_payload("progressions")

    def stub_progressed(**_kwargs):
        return [
            {
                "when_iso": "2024-03-01T00:00:00Z",
                "moving": "Venus",
                "target": "natal_Mars",
                "aspect": 90,
                "orb": 0.25,
                "applying": True,
                "retrograde": False,
                "speed_deg_per_day": 0.92,
            }
        ]

    monkeypatch.setattr(
        "astroengine.api.routers.scan.progressed_natal_aspects",
        stub_progressed,
    )

    response = client.post("/v1/scan/progressions", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["method"] == "progressions"
    assert data["count"] == 1
    assert data["hits"][0]["moving"] == "Venus"
    assert data["hits"][0]["retrograde"] is False
    assert data["hits"][0]["speed_deg_per_day"] == pytest.approx(0.92)
    assert data["hits"][0]["metadata"]["retrograde"] is False
    assert data["hits"][0]["metadata"]["speed_deg_per_day"] == pytest.approx(0.92)


def test_scan_progressions_streaming(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _base_payload("progressions")

    def stub_progressed(**_kwargs):
        yield {
            "when_iso": "2024-03-01T00:00:00Z",
            "moving": "Venus",
            "target": "natal_Mars",
            "aspect": 90,
            "orb": 0.25,
        }
        yield {
            "when_iso": "2024-06-01T00:00:00Z",
            "moving": "Mars",
            "target": "natal_Sun",
            "aspect": 120,
            "orb": 0.5,
        }

    monkeypatch.setattr(
        "astroengine.api.routers.scan.progressed_natal_aspects",
        stub_progressed,
    )

    response = client.post("/v1/scan/progressions?stream=true", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    lines = [json.loads(line) for line in response.text.strip().splitlines() if line.strip()]
    assert lines[0]["event"] == "metadata"
    assert lines[1]["event"] == "hit"
    assert lines[1]["data"]["moving"] == "Venus"
    assert lines[-1]["event"] == "summary"
    assert lines[-1]["count"] == 2


def test_scan_directions_endpoint(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _base_payload("directions")

    def stub_directions(**_kwargs):
        return [
            SimpleNamespace(
                when_iso="2024-04-10T00:00:00Z",
                moving="Mars",
                target="natal_Sun",
                aspect=120,
                orb=0.5,
                applying_or_separating="applying",
            )
        ]

    monkeypatch.setattr(
        "astroengine.api.routers.scan.solar_arc_natal_aspects",
        stub_directions,
    )

    response = client.post("/v1/scan/directions", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["method"] == "directions"
    assert body["count"] == 1
    assert body["hits"][0]["aspect"] == 120


def test_scan_streaming_rejects_export(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _base_payload("progressions")
    payload["export"] = {"path": "out.json", "format": "json"}

    monkeypatch.setattr(
        "astroengine.api.routers.scan.progressed_natal_aspects",
        lambda **_kwargs: [],
    )

    response = client.post("/v1/scan/progressions?stream=true", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "streaming responses do not support export payloads"


def test_scan_transits_not_implemented(client: TestClient) -> None:
    payload = _base_payload("transits")
    response = client.post("/v1/scan/transits", json=payload)
    assert response.status_code == 501


def test_scan_returns_endpoint(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _base_payload("returns")

    def stub_returns(_natal_jd, _start_jd, _end_jd, *, kind: str):
        return [
            SimpleNamespace(
                ts="2024-07-01T12:00:00Z",
                body="Sun" if kind == "solar" else "Moon",
                method=kind,
                jd=0.0,
                longitude=0.0,
            )
        ]

    class DummyAdapter:
        def julian_day(self, dt: datetime) -> float:
            return dt.replace(tzinfo=UTC).timestamp() / 86400.0

    monkeypatch.setattr(
        "astroengine.api.routers.scan.solar_lunar_returns",
        stub_returns,
    )
    monkeypatch.setattr(
        "astroengine.api.routers.scan.SwissEphemerisAdapter.get_default_adapter",
        classmethod(lambda cls: DummyAdapter()),
    )

    response = client.post("/v1/scan/returns", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["method"] == "returns"
    assert data["count"] == 1
    assert data["hits"][0]["moving"] in {"Sun", "Moon"}
