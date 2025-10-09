from __future__ import annotations

import importlib
import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("ASTROENGINE_ENABLE_HTTP_TESTS", "1")


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    monkeypatch.setenv("ASTROENGINE_HOME", str(tmp_path))
    monkeypatch.setenv("ASTROENGINE_ENABLE_HTTP_TESTS", "1")

    import astroengine.userdata.vault as vault

    importlib.reload(vault)
    globals()["vault"] = vault

    import astroengine.api.routers.natals as natals_router

    importlib.reload(natals_router)

    from astroengine.api import create_app

    app = create_app()
    return TestClient(app)


def test_upsert_persists_configuration_and_returns_snapshot(client: TestClient, tmp_path: Path) -> None:
    payload = {
        "name": "Configurable Chart",
        "utc": "2000-01-01T00:00:00Z",
        "lat": 12.34,
        "lon": 56.78,
        "tz": "UTC",
        "place": "Test Location",
        "houses": {"system": "W"},
        "zodiac": {"type": "SIDEREAL", "ayanamsa": "Krishnamurti"},
    }

    response = client.put("/v1/natals/test-subject", json=payload)
    assert response.status_code == 201
    body = response.json()

    assert body["houses"]["system"] == "whole_sign"
    assert body["zodiac"]["type"] == "sidereal"
    assert body["zodiac"]["ayanamsa"] == "krishnamurti"

    fetch = client.get("/v1/natals/test-subject")
    assert fetch.status_code == 200
    fetched = fetch.json()
    assert fetched["houses"] == body["houses"]
    assert fetched["zodiac"] == body["zodiac"]

    saved = tmp_path / "natals" / "test-subject.json"
    assert saved.exists()
    snapshot = json.loads(saved.read_text(encoding="utf-8"))
    assert snapshot["houses"]["system"] == "whole_sign"
    assert snapshot["zodiac"]["type"] == "sidereal"
    assert snapshot["zodiac"]["ayanamsa"] == "krishnamurti"
