from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.routers.aspects import router as aspects_router
from tests.helpers import LinearEphemeris, build_app, patch_aspects_provider


def test_post_aspects_search_minimal():
    t0 = datetime(2025, 1, 1, tzinfo=UTC)
    eph = LinearEphemeris(
        t0,
        base={"Mars": 10.0, "Venus": 0.0},
        rates={"Mars": 0.2, "Venus": 1.0},
    )
    with patch_aspects_provider(eph):
        app = build_app(aspects_router)
        client = TestClient(app)

        payload = {
            "objects": ["Mars", "Venus"],
            "aspects": ["sextile"],
            "harmonics": [],
            "window": {
                "start": t0.isoformat(),
                "end": (t0 + timedelta(days=100)).isoformat(),
            },
            "step_minutes": 360,
            "limit": 10,
            "offset": 0,
            "order_by": "time",
            "orb_policy_inline": {
                "per_aspect": {"sextile": 3.0},
                "adaptive_rules": {},
            },
        }

        response = client.post("/aspects/search", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert set(data.keys()) == {"hits", "bins", "paging"}
        assert data["paging"]["limit"] == 10
        assert isinstance(data["hits"], list)
        assert data["hits"], "expected at least one hit"
