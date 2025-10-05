"""Tests for HTTP compression helpers."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from astroengine.utils.json import has_orjson
from astroengine.web.middleware import configure_compression

try:  # pragma: no cover - optional dependency missing
    from fastapi.responses import ORJSONResponse
except ImportError:  # pragma: no cover
    ORJSONResponse = JSONResponse  # type: ignore[assignment]

try:  # pragma: no cover - optional router dependencies missing in CI
    from app.main import app as main_app
except ImportError:  # pragma: no cover
    main_app = None  # type: ignore[assignment]


def _build_test_app() -> FastAPI:
    app = FastAPI(default_response_class=ORJSONResponse)
    configure_compression(app, minimum_size=0, compresslevel=6)

    @app.get("/payload")
    def payload() -> dict[str, str]:
        return {"message": "x" * 2048}

    return app


@pytest.mark.skipif(main_app is None, reason="app.main unavailable in test environment")
def test_main_app_uses_orjson_response_class() -> None:
    """Ensure the production app prefers ``orjson`` when available."""

    if has_orjson():
        assert main_app.default_response_class is ORJSONResponse
    else:
        assert main_app.default_response_class is JSONResponse


def test_gzip_compression_enabled() -> None:
    """Clients requesting gzip should receive gzip encoded payloads."""

    app = _build_test_app()
    client = TestClient(app)
    response = client.get("/payload", headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 200
    assert response.headers.get("content-encoding") == "gzip"
    assert response.json() == {"message": "x" * 2048}


def test_deflate_compression_enabled() -> None:
    """Clients requesting deflate without gzip fallback should be supported."""

    app = _build_test_app()
    client = TestClient(app)
    response = client.get("/payload", headers={"Accept-Encoding": "deflate"})
    assert response.status_code == 200
    assert response.headers.get("content-encoding") == "deflate"
    assert response.json() == {"message": "x" * 2048}


def test_gzip_preferred_over_deflate_when_available() -> None:
    """When both encodings are accepted, gzip should win."""

    app = _build_test_app()
    client = TestClient(app)
    response = client.get(
        "/payload", headers={"Accept-Encoding": "gzip, deflate"}
    )
    assert response.status_code == 200
    assert response.headers.get("content-encoding") == "gzip"
