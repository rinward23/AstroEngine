from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from fastapi.testclient import TestClient

from app.routers.aspects import router as aspects_router
from app.routers.policies import router as policies_router
from app.routers.transits import router as transits_router


def build_app() -> FastAPI:
    app = FastAPI(default_response_class=ORJSONResponse)
    app.include_router(aspects_router)
    app.include_router(transits_router)
    app.include_router(policies_router)
    return app


def test_openapi_has_examples():
    app = build_app()
    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()

    components = spec["components"]["schemas"]

    aspect_req_example = components["AspectSearchRequest"]["example"]
    assert aspect_req_example["objects"] == ["Sun", "Moon", "Mars", "Venus"]
    assert aspect_req_example["window"]["end"] == "2025-03-01T00:00:00Z"

    aspect_resp_example = components["AspectSearchResponse"]["example"]
    assert aspect_resp_example["hits"][0]["aspect"] == "sextile"

    score_examples_raw = components["ScoreSeriesRequest"].get("examples", {})
    if isinstance(score_examples_raw, list):
        scan_example = next(
            (ex for ex in score_examples_raw if isinstance(ex, dict) and "scan" in ex.get("value", {})),
            None,
        )
        hits_example = next(
            (ex for ex in score_examples_raw if isinstance(ex, dict) and "hits" in ex.get("value", {})),
            None,
        )
    else:
        scan_example = score_examples_raw.get("scan") if isinstance(score_examples_raw, dict) else None
        hits_example = score_examples_raw.get("hits") if isinstance(score_examples_raw, dict) else None

    assert scan_example is not None and hits_example is not None
    assert scan_example["value"]["scan"]["objects"] == ["Mars", "Venus"]
    assert hits_example["value"]["hits"][0]["severity"] == 0.6

    score_resp_example = components["ScoreSeriesResponse"]["example"]
    assert score_resp_example["daily"][0]["score"] == 0.62

    policy_create_example = components["OrbPolicyCreate"]["example"]
    assert policy_create_example["per_aspect"]["square"] == 6.0

    policy_out_example = components["OrbPolicyOut"]["example"]
    assert policy_out_example["id"] == 1

    policy_list_example = components["OrbPolicyListOut"]["example"]
    assert policy_list_example["paging"]["limit"] == 50

    aspects_post = spec["paths"]["/aspects/search"]["post"]
    assert aspects_post["summary"].lower().startswith("search aspects")
    assert aspects_post["operationId"] == "plus_aspects_search"

    score_post = spec["paths"]["/transits/score-series"]["post"]
    assert score_post["summary"].lower().startswith("daily")
    assert score_post["operationId"] == "plus_score_series"

    policies_get = spec["paths"]["/policies"]["get"]
    assert policies_get["operationId"] == "plus_list_policies"
    assert policies_get["summary"].lower().startswith("list orb policies")

    policies_post = spec["paths"]["/policies"]["post"]
    assert policies_post["operationId"] == "plus_create_policy"
