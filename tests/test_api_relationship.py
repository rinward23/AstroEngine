from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.relationship import router as relationship_router
from app.routers import aspects as aspects_module


class LinearEphemeris:
    """Synthetic linear ephemeris used for deterministic Davison tests."""

    def __init__(self, t0, base, rates):
        self.t0 = t0
        self.base = base
        self.rates = rates

    def __call__(self, ts):
        dt_days = (ts - self.t0).total_seconds() / 86400.0
        return {
            key: (self.base.get(key, 0.0) + self.rates.get(key, 0.0) * dt_days) % 360.0
            for key in self.base
        }


def build_app(provider=None):
    app = FastAPI()
    if provider is not None:
        aspects_module.position_provider = provider
        if hasattr(aspects_module, "_cached"):
            aspects_module._cached = None
    app.include_router(relationship_router)
    return app


POS_A = {"Sun": 350.0, "Moon": 20.0, "Mars": 100.0}
POS_B = {"Sun": 10.0, "Moon": 80.0, "Venus": 200.0}


def test_synastry_endpoint():
    app = build_app()
    client = TestClient(app)
    payload = {
        "posA": POS_A,
        "posB": POS_B,
        "aspects": ["conjunction", "sextile", "trine", "square", "opposition"],
        "orb_policy_inline": {
            "per_aspect": {
                "conjunction": 8.0,
                "sextile": 3.0,
                "trine": 6.0,
                "square": 6.0,
                "opposition": 7.0,
            }
        },
    }
    response = client.post("/relationship/synastry", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert {"hits", "grid", "overlay", "scores"} <= set(data.keys())
    assert any(hit["a"] == "Sun" and hit["b"] == "Sun" for hit in data["hits"])


def test_composite_endpoint():
    app = build_app()
    client = TestClient(app)
    response = client.post("/relationship/composite", json={"posA": POS_A, "posB": POS_B})
    assert response.status_code == 200
    data = response.json()
    assert abs(data["positions"]["Sun"] - 0.0) < 1e-9


def test_davison_endpoint_mid_time_positions():
    t0 = datetime(2025, 1, 1, tzinfo=timezone.utc)
    eph = LinearEphemeris(t0, base={"Sun": 10.0, "Venus": 40.0}, rates={"Sun": 1.0, "Venus": 1.2})
    app = build_app(eph)
    client = TestClient(app)

    payload = {
        "dtA": t0.isoformat(),
        "dtB": (t0 + timedelta(days=10)).isoformat(),
        "locA": {"lat_deg": 10.0, "lon_deg_east": 20.0},
        "locB": {"lat_deg": -10.0, "lon_deg_east": 40.0},
        "bodies": ["Sun", "Venus"],
    }
    response = client.post("/relationship/davison", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert abs(data["positions"]["Sun"] - 15.0) < 1e-9
    assert abs(data["positions"]["Venus"] - 46.0) < 1e-9
    assert data["midpoint_time_utc"].startswith((t0 + timedelta(days=5)).isoformat()[:16])
