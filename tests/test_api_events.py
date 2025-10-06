from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from fastapi.testclient import TestClient

from app.routers import aspects as aspects_module
from app.routers.events import router as events_router


class LinearEphemeris:
    """Synthetic ephemeris where bodies move linearly in longitude."""

    def __init__(self, t0, base, rates):
        self.t0 = t0
        self.base = base
        self.rates = rates

    def __call__(self, ts):
        dt_days = (ts - self.t0).total_seconds() / 86400.0
        return {
            body: (self.base.get(body, 0.0) + self.rates.get(body, 0.0) * dt_days) % 360.0
            for body in self.base
        }


def build_app(provider):
    app = FastAPI(default_response_class=ORJSONResponse)
    aspects_module.position_provider = provider
    if hasattr(aspects_module, "_cached"):
        aspects_module._cached = None
    app.include_router(events_router)
    return app


def test_combust_cazimi_api():
    t0 = datetime(2025, 1, 1, tzinfo=UTC)
    eph = LinearEphemeris(
        t0,
        base={"Sun": 0.0, "Mercury": 0.5},
        rates={"Sun": 0.0, "Mercury": -0.1},
    )
    app = build_app(eph)
    client = TestClient(app)

    payload = {
        "window": {
            "start": t0.isoformat(),
            "end": (t0 + timedelta(days=20)).isoformat(),
        },
        "planet": "Mercury",
        "step_minutes": 10,
        "cfg": {
            "cazimi_deg": 0.2667,
            "combust_deg": 8.0,
            "under_beams_deg": 15.0,
        },
    }
    r = client.post("/events/combust-cazimi", json=payload)
    assert r.status_code == 200
    data = r.json()
    kinds = {iv["kind"] for iv in data}
    assert "cazimi" in kinds


def test_voc_moon_api():
    t0 = datetime(2025, 1, 1, tzinfo=UTC)
    eph = LinearEphemeris(
        t0,
        base={"Moon": 2.0, "Sun": 180.0},
        rates={"Moon": 13.0},
    )
    app = build_app(eph)
    client = TestClient(app)

    payload = {
        "window": {
            "start": t0.isoformat(),
            "end": (t0 + timedelta(days=3)).isoformat(),
        },
        "aspects": ["conjunction"],
        "other_objects": ["Sun"],
        "step_minutes": 120,
        "orb_policy_inline": {"per_aspect": {"conjunction": 8.0}},
    }
    r = client.post("/events/voc-moon", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list) and len(data) >= 1
    assert data[0]["kind"] == "voc_moon"


def test_returns_api():
    t0 = datetime(2025, 1, 1, tzinfo=UTC)
    eph = LinearEphemeris(t0, base={"Sun": 10.0}, rates={"Sun": 1.0})
    app = build_app(eph)
    client = TestClient(app)

    payload = {
        "window": {
            "start": (t0 + timedelta(hours=1)).isoformat(),
            "end": (t0 + timedelta(days=380)).isoformat(),
        },
        "body": "Sun",
        "target_lon": 10.0,
        "step_minutes": 720,
    }
    r = client.post("/events/returns", json=payload)
    assert r.status_code == 200
    data = r.json()
    expected = t0 + timedelta(days=360)
    assert any(
        abs(
            (
                datetime.fromisoformat(iv["start"]).replace(tzinfo=UTC)
                - expected
            ).total_seconds()
        )
        <= 60
        for iv in data
    )
