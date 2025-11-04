from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi import FastAPI
from fastapi.testclient import TestClient

from astroengine.api.routers import scan


@pytest.fixture(scope="module")
def client() -> TestClient:
    app = FastAPI()
    app.include_router(scan.router, prefix="/scan")
    return TestClient(app)


def _minimal_payload() -> dict[str, object]:
    return {
        "method": "progressions",
        "natal_inline": {"ts": "2024-01-01T00:00:00Z"},
        "from": "2024-02-01T00:00:00Z",
        "to": "2024-03-01T00:00:00Z",
    }


def test_transit_scan_request_instantiates_from_strings() -> None:
    payload = scan._normalize_scan_payload(_minimal_payload())
    request = scan.TransitScanRequest(**payload)

    natal_iso, start_iso, end_iso = request.iso_tuple()

    assert natal_iso.endswith("Z")
    assert start_iso.endswith("Z")
    assert end_iso.endswith("Z")
    assert request.orb == pytest.approx(1.0)
    assert request.step_days == pytest.approx(1.0)


def test_returns_scan_request_instantiates_from_aliases() -> None:
    payload = {
        "natal_ts": "2024-04-01T00:00:00Z",
        "start_ts": "2024-05-01T00:00:00Z",
        "end_ts": "2024-06-01T00:00:00Z",
        "bodies": ["Moon"],
    }

    request = scan.ReturnsScanRequest(**payload)
    natal_iso, start_iso, end_iso = request.iso_tuple()

    assert natal_iso.endswith("Z")
    assert start_iso.endswith("Z")
    assert end_iso.endswith("Z")
    assert request.bodies == ["Moon"]


def test_progressions_route_accepts_minimal_payload(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "astroengine.api.routers.scan.progressed_natal_aspects",
        lambda **_kwargs: [],
    )

    response = client.post("/scan/progressions", json=_minimal_payload())

    assert response.status_code == 200
    payload = response.json()
    assert payload["method"] == "progressions"
    assert payload["count"] == 0
