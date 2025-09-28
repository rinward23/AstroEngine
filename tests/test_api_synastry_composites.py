from datetime import datetime, timedelta, timezone

import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.rel import router as rel_router
from app.routers import aspects as aspects_module


class LinearEphemeris:
    def __init__(self, t0, base, rates):
        self.t0 = t0
        self.base = base
        self.rates = rates

    def __call__(self, ts):
        dt_days = (ts - self.t0).total_seconds() / 86400.0
        return {
            k: (self.base.get(k, 0.0) + self.rates.get(k, 0.0) * dt_days) % 360.0
            for k in self.base
        }


def build_app(provider=None):
    app = FastAPI()
    if provider is not None:
        aspects_module.position_provider = provider
        if hasattr(aspects_module, "_cached"):
            aspects_module._cached = None  # type: ignore[attr-defined]
    app.include_router(rel_router)
    return app


def test_synastry_compute_basic():
    app = build_app()
    client = TestClient(app)

    payload = {
        "pos_a": {"Mars": 10.0, "Sun": 0.0},
        "pos_b": {"Venus": 70.0, "Moon": 180.0},
        "aspects": ["sextile", "trine", "square", "conjunction"],
        "orb_policy_inline": {
            "per_aspect": {
                "sextile": 3.0,
                "square": 6.0,
                "trine": 6.0,
                "conjunction": 8.0,
            }
        },
    }

    r = client.post("/synastry/compute", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert any(
        h["a_obj"] == "Mars" and h["b_obj"] == "Venus" and h["aspect"] == "sextile"
        for h in data["hits"]
    )
    assert data["grid"]["counts"]["Mars"]["Venus"] == 1


def test_composites_midpoint_and_davison():
    t0 = datetime(2025, 1, 1, tzinfo=timezone.utc)
    eph = LinearEphemeris(t0, base={"Sun": 0.0, "Venus": 20.0}, rates={"Sun": 1.0, "Venus": 1.2})
    app = build_app(eph)
    client = TestClient(app)

    r = client.post(
        "/composites/midpoint",
        json={
            "pos_a": {"Sun": 10.0, "Moon": 200.0},
            "pos_b": {"Sun": 50.0, "Moon": 220.0},
            "objects": ["Sun", "Moon"],
        },
    )
    assert r.status_code == 200
    cm = r.json()
    assert abs(cm["positions"]["Sun"] - 30.0) < 1e-9
    assert abs(cm["positions"]["Moon"] - 210.0) < 1e-9

    dt_a = t0
    dt_b = t0 + timedelta(days=10)
    r = client.post(
        "/composites/davison",
        json={
            "objects": ["Sun", "Venus"],
            "dt_a": dt_a.isoformat(),
            "dt_b": dt_b.isoformat(),
        },
    )
    assert r.status_code == 200
    dv = r.json()
    assert abs(dv["positions"]["Sun"] - 5.0) < 1e-6
    assert abs(dv["positions"]["Venus"] - 26.0) < 1e-6



def test_synastry_etag_and_cache_headers():
    app = build_app()
    client = TestClient(app)

    payload = {
        "pos_a": {"Sun": 12.0, "Mercury": 45.0},
        "pos_b": {"Moon": 210.0, "Venus": 124.0},
        "aspects": ["trine", "square", "conjunction"],
    }

    first = client.post("/synastry/compute", json=payload)
    assert first.status_code == 200
    etag = first.headers.get("etag")
    assert etag
    assert first.headers.get("X-Cache-Status") in {"compute", "fallback"}

    second = client.post("/synastry/compute", json=payload, headers={"If-None-Match": etag})
    assert second.status_code == 304
    assert second.headers.get("X-Cache-Status") == "etag"

    third = client.post("/synastry/compute", json=payload)
    assert third.status_code == 200
    assert third.headers.get("X-Cache-Status") in {"lru", "redis"}

