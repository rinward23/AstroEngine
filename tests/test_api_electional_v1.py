from datetime import UTC, datetime

from fastapi.testclient import TestClient

from astroengine.api import create_app
from astroengine.electional.solver import SampleContext, SwissElectionalProvider
from astroengine.ephemeris import BodyPosition


def _body(name: str, lon: float) -> BodyPosition:
    return BodyPosition(
        body=name,
        julian_day=0.0,
        longitude=lon,
        latitude=0.0,
        distance_au=1.0,
        speed_longitude=0.0,
        speed_latitude=0.0,
        speed_distance=0.0,
        declination=0.0,
        speed_declination=0.0,
    )


def test_electional_search_endpoint(monkeypatch):
    t0 = datetime(2026, 3, 20, 12, 0, tzinfo=UTC)
    iso = t0.isoformat().replace("+00:00", "Z")

    context = SampleContext(
        ts=t0,
        iso=iso,
        positions={
            "Venus": _body("Venus", 100.0),
            "Moon": _body("Moon", 10.0),
            "Sun": _body("Sun", 14.0),
            "Mars": _body("Mars", 210.0),
            "Saturn": _body("Saturn", 300.0),
        },
        axes={"asc": 340.0, "desc": 160.0, "mc": 250.0, "ic": 70.0},
    )

    class StubSwissProvider(SwissElectionalProvider):  # type: ignore[misc]
        def __init__(self, *args, **kwargs):
            self._context = context

        def context(self, ts: datetime) -> SampleContext:
            return self._context

    monkeypatch.setattr("astroengine.electional.solver.SwissElectionalProvider", StubSwissProvider)

    app = create_app()
    client = TestClient(app)

    payload = {
        "start": iso,
        "end": iso,
        "step_minutes": 60,
        "location": {"lat": 0.0, "lon": 0.0},
        "constraints": [
            {"aspect": {"body": "venus", "target": "asc", "type": "trine", "max_orb": 1.0}},
            {"moon": {"void_of_course": False, "max_orb": 6.0}},
            {"malefic_to_angles": {"allow": False, "max_orb": 3.0}},
        ],
    }

    response = client.post("/v1/electional/search", json=payload)
    assert response.status_code == 200, response.json()
    data = response.json()
    assert data["count"] == 1
    candidate = data["candidates"][0]
    assert candidate["ts"].startswith("2026-03-20T12:00:00")
    assert candidate["score"] > 0
    assert all(item["passed"] for item in candidate["evaluations"])
