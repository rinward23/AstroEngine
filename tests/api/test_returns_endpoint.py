from __future__ import annotations

import importlib
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

pytest.importorskip(
    "swisseph",
    reason="pyswisseph required for return endpoint checks.",
)


def _iso(dt: datetime) -> str:
    aware = dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
    return aware.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def test_returns_endpoint_emits_requested_types(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ASTROENGINE_HOME", str(tmp_path))

    # Ensure repositories reflect the temporary configuration root.
    from astroengine.userdata import vault as vault_module

    importlib.reload(vault_module)

    natal = vault_module.Natal(
        natal_id="test-natal",
        name="Test",
        utc=_iso(datetime(2000, 1, 1, tzinfo=timezone.utc)),
        lat=0.0,
        lon=0.0,
        tz="UTC",
        place=None,
    )
    vault_module.save_natal(natal)

    import astroengine.api as api

    importlib.reload(api)

    client = TestClient(api.app)

    response = client.get(
        "/v1/returns",
        params={"natal_id": natal.natal_id, "year": 2024, "types": "solar,lunar"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["timezone"] == "UTC"
    assert data["solar"]
    assert isinstance(data["lunar"], list)

    from astroengine.config import load_settings

    assert len(data["lunar"]) == load_settings().returns_ingress.lunar_count
