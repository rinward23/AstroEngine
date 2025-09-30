from fastapi.testclient import TestClient

from astroengine.api import create_app

app = create_app()
client = TestClient(app)

NATAL = {
    "datetime": "1984-10-17T04:30:00Z",
    "lat": 40.7128,
    "lon": -74.0060,
}


def test_chart_endpoint_returns_nakshatra_data():
    response = client.post(
        "/v1/vedic/chart",
        json={**NATAL, "ayanamsa": "lahiri"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"]["zodiac"] == "sidereal"
    moon = next(body for body in payload["bodies"] if body["name"] == "Moon")
    assert "nakshatra" in moon
    assert "lord" in moon


def test_vimshottari_endpoint_structure():
    response = client.post(
        "/v1/vedic/dasha/vimshottari",
        json={
            "natal": NATAL,
            "ayanamsa": "lahiri",
            "levels": 2,
            "options": {"year_basis": 365.25, "anchor": "exact"},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"]["ayanamsa"] == "lahiri"
    assert payload["periods"]
    first = payload["periods"][0]
    assert first["ruler"]
    assert first["start"].endswith("Z")


def test_varga_endpoint_returns_d9():
    response = client.post(
        "/v1/vedic/varga",
        json={
            "natal": NATAL,
            "ayanamsa": "lahiri",
            "charts": ["D9", "D10"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "D9" in data["charts"]
    assert "Sun" in data["charts"]["D9"]
