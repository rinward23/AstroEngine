from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.interpret import router as interpret_router

APP = FastAPI()
APP.include_router(interpret_router)
CLIENT = TestClient(APP)

SYN_HITS = [
    {"a": "Sun", "b": "Moon", "aspect": "trine", "severity": 0.6},
    {"a": "Venus", "b": "Mars", "aspect": "conjunction", "severity": 0.5},
    {"a": "Saturn", "b": "Venus", "aspect": "square", "severity": 0.4},
]


def test_rulepacks_list():
    response = CLIENT.get("/interpret/rulepacks")
    assert response.status_code == 200
    data = response.json()
    assert data["meta"]["count"] >= 1


def test_relationship_findings_with_default_rulepack():
    payload = {"scope": "synastry", "hits": SYN_HITS, "top_k": 2}
    response = CLIENT.post("/interpret/relationship", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["findings"]) <= 2


def test_inline_rules_override():
    rules_inline = [
        {
            "id": "only_venus_mars",
            "scope": "synastry",
            "when": {
                "bodies": ["Venus", "Mars"],
                "aspect_in": ["conjunction"],
                "min_severity": 0.2,
            },
            "score": 2.0,
            "text": "chemistry",
        }
    ]
    payload = {"scope": "synastry", "hits": SYN_HITS, "rules_inline": rules_inline}
    response = CLIENT.post("/interpret/relationship", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["findings"]) == 1
    assert data["findings"][0]["text"] == "chemistry"


def test_composite_positions_rulepack():
    payload = {
        "scope": "composite",
        "positions": {"Venus": 5.0},
        "rulepack_id": "relationship_basic",
    }
    response = CLIENT.post("/interpret/relationship", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["findings"], list)
