import pytest

pytest.importorskip("fastapi")
pytest.importorskip("markdown_it")
from fastapi.testclient import TestClient

from app.main import app as plus_app
from astroengine.api import app as astro_app


def test_lots_presets_etag() -> None:
    client = TestClient(astro_app)
    response = client.get("/v1/lots/presets")
    assert response.status_code == 200
    assert "ETag" in response.headers
    assert "Cache-Control" in response.headers
    etag = response.headers["ETag"]
    assert "immutable" in response.headers["Cache-Control"]

    cached = client.get("/v1/lots/presets", headers={"If-None-Match": etag})
    assert cached.status_code == 304
    assert cached.headers["ETag"] == etag


def test_plus_lots_catalog_etag() -> None:
    client = TestClient(plus_app)
    response = client.get("/lots/catalog")
    assert response.status_code == 200
    assert "ETag" in response.headers
    assert response.headers["Cache-Control"].startswith("public")
    etag = response.headers["ETag"]

    cached = client.get("/lots/catalog", headers={"If-None-Match": etag})
    assert cached.status_code == 304
    assert cached.headers["ETag"] == etag
