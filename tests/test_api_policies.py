from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.policies import router as policies_router


def build_app():
    app = FastAPI()
    app.include_router(policies_router)
    return app


def test_policy_crud_cycle(tmp_path, monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.db.base import Base
    from app.db import models  # ensure models imported
    from app.db import session as dbsession

    test_db = f"sqlite:///{tmp_path}/test.db"
    engine = create_engine(test_db, future=True)
    Base.metadata.create_all(engine)
    dbsession.engine = engine
    dbsession.SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    app = build_app()
    client = TestClient(app)

    payload = {
        "name": "classic",
        "description": "Default classical orbs",
        "per_aspect": {"sextile": 3.0, "square": 6.0},
        "adaptive_rules": {"luminaries_factor": 0.9},
    }
    r = client.post("/policies", json=payload)
    assert r.status_code == 201
    pid = r.json()["id"]

    r = client.get(f"/policies/{pid}")
    assert r.status_code == 200
    assert r.json()["name"] == "classic"

    r = client.put(f"/policies/{pid}", json={"description": "Updated"})
    assert r.status_code == 200 and r.json()["description"] == "Updated"

    r = client.get("/policies?limit=10&offset=0")
    assert r.status_code == 200 and r.json()["paging"]["total"] >= 1

    r = client.delete(f"/policies/{pid}")
    assert r.status_code == 204
