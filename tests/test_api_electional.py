from datetime import datetime, timedelta, timezone
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from fastapi.testclient import TestClient

from app.routers.electional import router as electional_router
from app.routers import aspects as aspects_module


# Synthetic ephemeris: linear motion
class LinearEphemeris:
    def __init__(self, t0, base, rates):
        self.t0, self.base, self.rates = t0, base, rates

    def __call__(self, ts):
        dt_days = (ts - self.t0).total_seconds() / 86400.0
        return {k: (self.base.get(k, 0.0) + self.rates.get(k, 0.0) * dt_days) % 360.0 for k in self.base}


def build_app(provider=None):
    app = FastAPI(default_response_class=ORJSONResponse)
    if provider is not None:
        aspects_module.position_provider = provider
        if hasattr(aspects_module, "_cached"):
            aspects_module._cached = None
    app.include_router(electional_router)
    return app


def test_electional_search_basic():
    t0 = datetime(2025, 1, 1, tzinfo=timezone.utc)
    eph = LinearEphemeris(
        t0,
        base={"Mars": 10.0, "Venus": 70.0, "Moon": 0.0, "Sun": 0.0},
        rates={"Mars": 0.2, "Venus": 1.0, "Moon": 13.0},
    )
    app = build_app(eph)
    client = TestClient(app)

    payload = {
        "window": {"start": t0.isoformat(), "end": (t0 + timedelta(days=40)).isoformat()},
        "window_minutes": 24 * 60,  # 1 day
        "step_minutes": 60,
        "top_k": 2,
        "avoid_voc_moon": False,
        "allowed_weekdays": None,
        "allowed_utc_ranges": [["06:00", "23:00"]],
        "orb_policy_inline": {"per_aspect": {"sextile": 3.0, "trine": 6.0, "conjunction": 8.0}},
        "required_aspects": [{"a": "Mars", "b": "Venus", "aspects": ["sextile"], "weight": 1.0}],
        "forbidden_aspects": [],
    }

    r = client.post("/electional/search", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "windows" in data and len(data["windows"]) >= 1
    w0 = data["windows"][0]
    for key in ("start", "end", "score", "avg_score", "samples", "top_instants", "breakdown"):
        assert key in w0


def test_electional_search_forbidden_penalty_and_voc_toggle():
    t0 = datetime(2025, 1, 1, tzinfo=timezone.utc)
    eph = LinearEphemeris(
        t0,
        base={"Sun": 0.0, "Saturn": 180.0, "Moon": 0.0, "Mars": 10.0, "Venus": 70.0},
        rates={"Sun": 0.0, "Saturn": 0.0, "Moon": 13.0},
    )
    app = build_app(eph)
    client = TestClient(app)

    payload = {
        "window": {"start": t0.isoformat(), "end": (t0 + timedelta(days=5)).isoformat()},
        "window_minutes": 12 * 60,
        "step_minutes": 120,
        "top_k": 1,
        "avoid_voc_moon": True,
        "allowed_weekdays": None,
        "allowed_utc_ranges": None,
        "orb_policy_inline": {"per_aspect": {"opposition": 7.0, "conjunction": 8.0, "sextile": 3.0, "trine": 6.0}},
        "required_aspects": [{"a": "Mars", "b": "Venus", "aspects": ["sextile", "trine"], "weight": 0.5}],
        "forbidden_aspects": [{"a": "Moon", "b": "Saturn", "aspects": ["opposition"], "penalty": 1.0}],
    }

    r = client.post("/electional/search", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert len(data["windows"]) == 1
