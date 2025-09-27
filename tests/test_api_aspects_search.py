from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import aspects as aspects_module
from app.routers.aspects import router as aspects_router


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
    app.include_router(aspects_router)
    return app


def test_post_aspects_search_minimal():
    t0 = datetime(2025, 1, 1, tzinfo=timezone.utc)
    eph = LinearEphemeris(
        t0,
        base={"Mars": 10.0, "Venus": 0.0},
        rates={"Mars": 0.2, "Venus": 1.0},
    )
    app = build_app(eph)
    client = TestClient(app)

    payload = {
        "objects": ["Mars", "Venus"],
        "aspects": ["sextile"],
        "harmonics": [],
        "window": {
            "start": t0.isoformat(),
            "end": (t0 + timedelta(days=100)).isoformat(),
        },
        "step_minutes": 360,
        "limit": 10,
        "offset": 0,
        "order_by": "time",
        "orb_policy_inline": {
            "per_aspect": {"sextile": 3.0},
            "adaptive_rules": {},
        },
    }

    response = client.post("/aspects/search", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {"hits", "bins", "paging"}
    assert data["paging"]["limit"] == 10
    assert isinstance(data["hits"], list)
    assert data["hits"], "expected at least one hit"
