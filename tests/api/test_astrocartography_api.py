from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from astroengine.analysis.astrocartography import AstrocartographyResult, MapLine
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


@pytest.mark.swiss
def test_astrocartography_endpoint_includes_parans(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("swisseph")
    _save_sample_natal()
    app = create_app()
    client = TestClient(app)

    response = client.get(
        "/v1/astrocartography",
        params={
            "natal_id": "sample",
            "bodies": "sun,moon",
            "line_types": "MC,IC,ASC,DSC",
            "show_parans": "true",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"]["parans"] is True

    paran_features = [
        feature
        for feature in payload["features"]
        if feature["geometry"]["type"] == "MultiPoint"
    ]
    assert paran_features, "Expected paran markers when show_parans=true"

    first = paran_features[0]["properties"]
    assert "primary" in first and "secondary" in first
    metadata = first.get("metadata", {})
    assert "angular_separation_deg" in metadata


def test_astrocartography_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    _save_sample_natal()

    dummy_result = AstrocartographyResult(
        lines=(
            MapLine(
                body="sun",
                kind="MC",
                coordinates=((0.0, 0.0), (10.0, 10.0)),
                metadata={"strength": 1.0},
            ),
        ),
        parans=(),
    )

    monkeypatch.setattr(
        "astroengine.api.routers.astrocartography.compute_astrocartography_lines",
        lambda *args, **kwargs: dummy_result,
    )

    app = create_app()
    client = TestClient(app)
    params = {"natal_id": "sample", "bodies": "sun"}

    for _ in range(10):
        ok = client.get("/v1/astrocartography", params=params)
        assert ok.status_code == 200

    limited = client.get("/v1/astrocartography", params=params)
    assert limited.status_code == 429
    detail = limited.json()["detail"]
    assert detail["code"] == "rate_limited"
    assert "please try again" in detail["message"].lower()
    assert int(limited.headers["Retry-After"]) >= 0
