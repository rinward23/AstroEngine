from datetime import datetime, timedelta, timezone

import pytest

pytest.importorskip("fastapi")

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.transits import router as transits_router
from app.routers import aspects as aspects_module


class LinearEphemeris:
    def __init__(self, t0, base, rates):
        self.t0, self.base, self.rates = t0, base, rates

    def __call__(self, ts):
        dt_days = (ts - self.t0).total_seconds() / 86400.0
        return {
            k: (self.base[k] + self.rates.get(k, 0.0) * dt_days) % 360.0
            for k in self.base
        }


def build_app(provider):
    app = FastAPI()
    aspects_module.position_provider = provider
    app.include_router(transits_router)
    return app


def test_score_series_from_scan():
    t0 = datetime(2025, 1, 1, tzinfo=timezone.utc)
    eph = LinearEphemeris(
        t0,
        base={"Mars": 10.0, "Venus": 0.0},
        rates={"Mars": 0.2, "Venus": 1.0},
    )
    app = build_app(eph)
    client = TestClient(app)

    payload = {
        "scan": {
            "objects": ["Mars", "Venus"],
            "aspects": ["sextile"],
            "harmonics": [],
            "window": {
                "start": t0.isoformat(),
                "end": (t0 + timedelta(days=40)).isoformat(),
            },
            "step_minutes": 360,
            "orb_policy_inline": {"per_aspect": {"sextile": 3.0}},
        }
    }
    response = client.post("/transits/score-series", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "daily" in data and "monthly" in data and data["meta"]["count_hits"] >= 0


def test_score_series_from_hits():
    app = build_app(lambda ts: {"Mars": 0.0, "Venus": 0.0})
    client = TestClient(app)

    hits = [
        {
            "a": "Mars",
            "b": "Venus",
            "aspect": "sextile",
            "exact_time": "2025-01-02T12:00:00Z",
            "orb": 0.1,
            "orb_limit": 3.0,
            "severity": 0.5,
        }
    ]
    response = client.post("/transits/score-series", json={"hits": hits})
    assert response.status_code == 200
    data = response.json()
    assert data["daily"][0]["score"] == 0.5


def test_score_series_from_hits_without_severity():
    from astroengine.core.scan_plus.ranking import severity as compute_severity

    app = build_app(lambda ts: {"Mars": 0.0, "Venus": 0.0})
    client = TestClient(app)

    hits = [
        {
            "a": "Mars",
            "b": "Venus",
            "aspect": "sextile",
            "exact_time": "2025-01-03T00:00:00Z",
            "orb": 0.0,
            "orb_limit": 3.0,
        }
    ]
    response = client.post("/transits/score-series", json={"hits": hits})
    assert response.status_code == 200
    data = response.json()
    expected = compute_severity("sextile", 0.0, 3.0)
    assert data["daily"][0]["score"] == pytest.approx(expected)
