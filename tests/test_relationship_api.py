"""Tests for the B-003 relationship API service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.relationship_api import ServiceSettings, create_app


class LinearEphemeris:
    def __init__(self, origin: datetime, base: dict[str, float], rates: dict[str, float]) -> None:
        self.origin = origin
        self.base = base
        self.rates = rates

    def __call__(self, ts: datetime) -> dict[str, float]:
        delta_days = (ts - self.origin).total_seconds() / 86400.0
        return {
            name: (self.base.get(name, 0.0) + self.rates.get(name, 0.0) * delta_days) % 360.0
            for name in self.base
        }


def build_client() -> TestClient:
    settings = ServiceSettings(rate_limit_per_minute=1000, enable_etag=True)
    app = create_app(settings)
    return TestClient(app)


def test_synastry_endpoint_returns_hits_and_etag():
    client = build_client()
    payload = {
        "positionsA": {
            "Sun": {"lon": 10.0},
            "Moon": {"lon": 200.0},
            "Venus": {"lon": 40.0},
        },
        "positionsB": {
            "Sun": {"lon": 190.0},
            "Moon": {"lon": 20.0},
            "Mars": {"lon": 45.0},
        },
        "min_severity": 0.1,
    }
    response = client.post("/v1/relationship/synastry", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["hits"], "Expected synastry hits"
    assert data["scores"]["overall"] > 0
    etag = response.headers.get("ETag")
    assert etag, "ETag header missing"
    cached = client.post(
        "/v1/relationship/synastry",
        json=payload,
        headers={"If-None-Match": etag},
    )
    assert cached.status_code == 304


def test_composite_endpoint_midpoint():
    client = build_client()
    payload = {
        "positionsA": {"Sun": {"lon": 350.0}, "Moon": {"lon": 20.0}},
        "positionsB": {"Sun": {"lon": 10.0}, "Moon": {"lon": 80.0}},
    }
    response = client.post("/v1/relationship/composite", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert abs(data["positions"]["Sun"]["lon"] - 0.0) < 1e-6
    assert abs(data["positions"]["Moon"]["lon"] - 50.0) < 1e-6


def test_davison_endpoint_with_stub(monkeypatch):
    client = build_client()
    origin = datetime(2025, 1, 1, tzinfo=timezone.utc)
    stub = LinearEphemeris(
        origin,
        base={"Sun": 10.0, "Venus": 20.0},
        rates={"Sun": 1.0, "Venus": 1.2},
    )

    def fake_provider(_name: str, _node_policy: str, bodies: list[str]):
        def _inner(ts: datetime) -> dict[str, float]:
            return stub(ts)

        return _inner

    monkeypatch.setattr("app.relationship_api.composite.make_position_provider", fake_provider)

    payload = {
        "birthA": {"when": origin.isoformat(), "lat": 10.0, "lon": 20.0},
        "birthB": {"when": (origin + timedelta(days=10)).isoformat(), "lat": -10.0, "lon": 40.0},
        "bodies": ["Sun", "Venus"],
        "eph": "swiss",
    }
    response = client.post("/v1/relationship/davison", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "positions" in data and set(data["positions"]) == {"Sun", "Venus"}
    assert abs(data["positions"]["Sun"]["lon"] - 15.0) < 1e-6
    assert abs(data["positions"]["Venus"]["lon"] - 26.0) < 1e-6
    mid = datetime.fromisoformat(data["mid_when"].replace("Z", "+00:00"))
    assert mid == origin + timedelta(days=5)


def test_rate_limit_headers_on_429():
    settings = ServiceSettings(rate_limit_per_minute=1, enable_etag=False)
    app = create_app(settings)
    client = TestClient(app)
    payload = {
        "positionsA": {"Sun": {"lon": 10.0}},
        "positionsB": {"Sun": {"lon": 190.0}},
    }
    first = client.post("/v1/relationship/composite", json=payload)
    assert first.status_code == 200
    second = client.post("/v1/relationship/composite", json=payload)
    assert second.status_code == 429
    assert second.headers.get("X-RateLimit-Reason") == "token_bucket"
    assert "Retry-After" in second.headers


def test_security_headers_with_hsts_enabled():
    settings = ServiceSettings(
        rate_limit_per_minute=10,
        enable_etag=False,
        tls_terminates_upstream=True,
        enable_hsts=True,
        hsts_max_age=86400,
    )
    app = create_app(settings)
    client = TestClient(app)
    response = client.get("/v1/healthz")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Permissions-Policy"] == "geolocation=(), microphone=()"
    assert response.headers["Strict-Transport-Security"].startswith("max-age=86400")
