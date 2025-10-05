"""Health endpoint tests for the Plus router."""

from __future__ import annotations

import pytest

pytest.importorskip(
    "PIL",
    reason="Pillow not installed; install extras with `pip install -e .[ui,reports]`.",
)

try:  # pragma: no cover - optional dependency in test environment
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover - FastAPI not installed
    TestClient = None  # type: ignore[assignment]

from astroengine.api_server import app

pytestmark = pytest.mark.skipif(
    app is None or TestClient is None, reason="FastAPI not available"
)


def test_health_plus_endpoint() -> None:
    client = TestClient(app)  # type: ignore[misc]
    response = client.get("/health/plus")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    client.close()
