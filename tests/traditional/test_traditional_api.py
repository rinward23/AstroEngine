from __future__ import annotations

from datetime import UTC, datetime

import pytest

pytest.importorskip(
    "PIL",
    reason="Pillow not installed; install extras with `pip install -e .[ui,reports]`.",
)

from fastapi.testclient import TestClient

from astroengine.api import create_app

client = TestClient(create_app())


_DEF_NATAL = {
    "moment": "1990-05-15T12:00:00+00:00",
    "latitude": 51.5074,
    "longitude": -0.1278,
}


def test_profections_api() -> None:
    body = {
        "natal": _DEF_NATAL,
        "start": "2020-05-15T12:00:00+00:00",
        "end": "2021-05-15T12:00:00+00:00",
        "mode": "hellenistic",
    }
    resp = client.post("/v1/traditional/profections", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["segments"]
    assert data["meta"]["mode"] == "hellenistic"


def test_zodiacal_releasing_api() -> None:
    body = {
        "natal": _DEF_NATAL,
        "lot_sign": "aries",
        "start": "2020-01-01T00:00:00+00:00",
        "end": "2030-01-01T00:00:00+00:00",
        "levels": 2,
        "source": "Spirit",
        "include_peaks": True,
    }
    resp = client.post("/v1/traditional/zr", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert "1" in data["levels"]
    assert data["lot"] == "Aries"
    assert data["levels"]["1"][0]["sign"]


def test_sect_api() -> None:
    body = {
        "moment": "2023-07-01T12:00:00+00:00",
        "latitude": 0.0,
        "longitude": 0.0,
    }
    resp = client.post("/v1/traditional/sect", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_day"] is True


def test_life_api() -> None:
    body = {
        "natal": _DEF_NATAL,
        "include_fortune": True,
    }
    resp = client.post("/v1/traditional/life", json=body)
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["hyleg"]["body"]
    assert payload["alcocoden"]["body"]
