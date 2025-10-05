from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from fastapi.testclient import TestClient

from astroengine.api.routers.interpret import router as interpret_router
from astroengine.interpret.store import get_rulepack_store


@pytest.fixture()
def api_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("AE_RULEPACK_DIR", str(tmp_path / "rulepacks"))
    monkeypatch.delenv("AE_RULEPACK_ALLOW_MUTATIONS", raising=False)
    get_rulepack_store.cache_clear()
    app = FastAPI(default_response_class=ORJSONResponse)
    app.include_router(interpret_router)
    return TestClient(app)


def test_rulepacks_list(api_client: TestClient) -> None:
    response = api_client.get("/v1/interpret/rulepacks")
    assert response.status_code == 200
    payload = response.json()
    assert payload["page"] == 1
    assert payload["page_size"] >= 1
    assert payload["total"] >= len(payload["items"])
    assert any(item["id"] == "relationship_basic" for item in payload["items"])


def test_relationship_findings_with_default_rulepack(api_client: TestClient) -> None:
    request = {
        "rulepack_id": "relationship_basic",
        "scope": "synastry",
        "synastry": {
            "hits": [
                {"a": "Sun", "b": "Moon", "aspect": "trine", "severity": 0.6},
                {"a": "Venus", "b": "Mars", "aspect": "conjunction", "severity": 0.5},
            ]
        },
    }
    response = api_client.post("/v1/interpret/relationship", json=request)
    assert response.status_code == 200
    body = response.json()
    assert body["rulepack"]["id"] == "relationship_basic"
    assert body["totals"]["count"] >= 1


def test_relationship_synastry_from_positions(api_client: TestClient) -> None:
    request = {
        "rulepack_id": "relationship_basic",
        "scope": "synastry",
        "synastry": {
            "positionsA": {"Sun": 10.0, "Moon": 120.0, "Venus": 200.0},
            "positionsB": {"Sun": 20.0, "Moon": 300.0, "Mars": 200.0},
            "aspects": [0, 60, 90, 120, 180],
        },
    }
    response = api_client.post("/v1/interpret/relationship", json=request)
    assert response.status_code == 200
    data = response.json()
    assert data["totals"]["count"] >= 1


def test_rulepack_upload_and_fetch(api_client: TestClient) -> None:
    rulepack = {
        "meta": {
            "id": "custom_pack",
            "name": "Custom Pack",
            "title": "Custom Relationship Insights",
            "description": "Test rulepack",
        },
        "rules": [
            {
                "id": "syn_custom",
                "scope": "synastry",
                "title": "Custom",
                "text": "custom",
                "score": 1.0,
                "when": {"bodies": ["Sun", "Moon"], "aspect_in": ["trine"], "min_severity": 0.1},
            }
        ],
    }
    response = api_client.post("/v1/interpret/rulepacks", json={"content": rulepack})
    assert response.status_code == 201
    meta = response.json()
    assert meta["id"] == "custom_pack"
    assert meta["version"] == 1

    response = api_client.get("/v1/interpret/rulepacks/custom_pack")
    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["id"] == "custom_pack"
    assert "ETag" in response.headers


def test_rulepack_lint(api_client: TestClient) -> None:
    lint_payload = {
        "meta": {"id": "lint_pack", "name": "Lint", "title": "Lint"},
        "rules": [
            {
                "id": "syn_lint",
                "scope": "synastry",
                "title": "Lint",
                "text": "lint",
                "when": {"bodies": ["Sun"], "aspect_in": ["trine"]},
            }
        ],
    }
    response = api_client.post("/v1/interpret/rulepacks/lint", json={"content": lint_payload})
    assert response.status_code == 200
    result = response.json()
    assert result["ok"] is True


def test_delete_rulepack_guarded(api_client: TestClient) -> None:
    response = api_client.delete("/v1/interpret/rulepacks/relationship_basic")
    assert response.status_code == 403
    error = response.json()
    assert error["code"] == "FORBIDDEN"
    assert error["message"]
