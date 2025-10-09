from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from fastapi.testclient import TestClient

from app.routers.lots import router as lots_router


def build_app():
    app = FastAPI(default_response_class=ORJSONResponse)
    app.include_router(lots_router)
    return app


def test_lots_catalog_lists_builtins():
    app = build_app()
    client = TestClient(app)
    response = client.get("/lots/catalog")
    assert response.status_code == 200
    data = response.json()
    names = [item["name"] for item in data["lots"]]
    assert "Fortune" in names and "Spirit" in names


def test_compute_fortune_day_and_custom_inline():
    app = build_app()
    client = TestClient(app)

    payload = {
        "positions": {"Asc": 100.0, "Sun": 10.0, "Moon": 70.0},
        "lots": ["Fortune", "Spirit"],
        "sect": "day",
        "custom_lots": [
            {
                "name": "LotOfTest",
                "day": "Asc + 15 - Sun",
                "night": "Asc + 15 - Sun",
                "register": False,
            }
        ],
    }

    response = client.post("/lots/compute", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert abs(data["positions"]["Fortune"] - 160.0) < 1e-9
    assert abs(data["positions"]["Spirit"] - 40.0) < 1e-9


def test_register_custom_lot_persists_for_catalog():
    app = build_app()
    client = TestClient(app)

    payload = {
        "positions": {"Asc": 200.0, "Sun": 10.0},
        "lots": ["LotOfPersist"],
        "sect": "day",
        "custom_lots": [
            {
                "name": "LotOfPersist",
                "day": "Asc + 15 - Sun",
                "night": "Asc + 15 - Sun",
                "register": True,
            }
        ],
    }

    response = client.post("/lots/compute", json=payload)
    assert response.status_code == 200

    response_catalog = client.get("/lots/catalog")
    assert response_catalog.status_code == 200
    names = [item["name"] for item in response_catalog.json()["lots"]]
    assert "LotOfPersist" in names
