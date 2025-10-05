from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from astroengine.api import create_app
from astroengine.userdata import vault


@pytest.fixture(autouse=True)
def _temp_vault(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ASTROENGINE_HOME", str(tmp_path))
    monkeypatch.setattr(vault, "BASE", tmp_path / "natals", raising=False)
    vault.BASE.mkdir(parents=True, exist_ok=True)


def _save_sample_natal() -> vault.Natal:
    natal = vault.Natal(
        natal_id="sample",
        name="Sample",
        utc="2020-12-21T13:00:00Z",
        lat=0.0,
        lon=0.0,
    )
    vault.save_natal(natal)
    return natal


@pytest.mark.swiss
def test_astrocartography_endpoint_returns_geojson(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("swisseph")
    _save_sample_natal()
    app = create_app()
    client = TestClient(app)

    response = client.get("/v1/astrocartography", params={"natal_id": "sample", "bodies": "jupiter"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "FeatureCollection"
    assert payload["features"], "Expected at least one feature in GeoJSON payload"
    first = payload["features"][0]
    assert first["type"] == "Feature"
    assert first["geometry"]["type"] == "LineString"
    assert len(first["geometry"]["coordinates"]) >= 2
