"""Regression tests for the topocentric API router."""

from __future__ import annotations

import importlib
import sys
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def reset_topocentric_module(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure a clean import of the router for each test."""

    monkeypatch.delitem(sys.modules, "astroengine.api.routers.topocentric", raising=False)


def _build_client() -> TestClient:
    module = importlib.import_module("astroengine.api.routers.topocentric")
    app = FastAPI()
    app.include_router(module.router)
    return TestClient(app)


def _iso(dt: datetime) -> str:
    return dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def test_endpoints_return_503_when_swiss_ephemeris_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """All endpoints should return HTTP 503 if Swiss Ephemeris is unavailable."""

    from astroengine.ephemeris import swe as swe_module

    monkeypatch.setattr(swe_module, "has_swe", lambda: False)

    def _unreachable() -> None:  # pragma: no cover - defensive guard
        raise AssertionError("Swiss Ephemeris should not be queried when unavailable")

    monkeypatch.setattr(swe_module, "swe", lambda: _unreachable())

    client = _build_client()

    observer = {"latitude_deg": 0.0, "longitude_deg": 0.0, "elevation_m": 0.0}
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 1, 2, tzinfo=timezone.utc)

    payloads = {
        "/topocentric/positions": {
            "body": 0,
            "moment": _iso(start),
            "observer": observer,
            "refraction": True,
        },
        "/topocentric/events": {
            "body": 0,
            "date": _iso(start),
            "observer": observer,
            "refraction": True,
        },
        "/topocentric/visibility": {
            "body": 0,
            "start": _iso(start),
            "end": _iso(end),
            "observer": observer,
            "constraints": {
                "min_altitude_deg": 0.0,
                "refraction": True,
                "horizon_dip_deg": 0.0,
                "step_seconds": 300,
            },
        },
        "/topocentric/heliacal": {
            "body": 0,
            "start": _iso(start),
            "end": _iso(end),
            "observer": observer,
            "profile": {
                "mode": "rising",
                "min_object_altitude_deg": 5.0,
                "sun_altitude_max_deg": -10.0,
                "sun_separation_min_deg": 12.0,
                "refraction": True,
                "search_window_hours": 2.0,
            },
        },
        "/topocentric/altaz/diagram": {
            "body": 0,
            "start": _iso(start),
            "end": _iso(end),
            "observer": observer,
            "refraction": True,
            "include_png": False,
        },
    }

    for path, payload in payloads.items():
        response = client.post(path, json=payload)
        assert response.status_code == 503
        assert response.json()["detail"] == "Swiss Ephemeris is not available"
