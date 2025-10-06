from __future__ import annotations

from datetime import UTC, datetime

import pytest

from astroengine.analysis import condition_report, score_accidental, score_essential
from astroengine.analysis import dignities as dignities_module
from astroengine.chart.natal import ChartLocation, NatalChart
from astroengine.ephemeris import BodyPosition, HousePositions


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    dignities_module._clear_caches()


def test_score_essential_sun_aries_exaltation() -> None:
    score = score_essential("Sun", 19.0)
    assert score >= 4


def test_score_accidental_penalises_cadent_retrograde() -> None:
    score = score_accidental("Saturn", True, 12, "night")
    assert score == -13


def test_condition_report_returns_component_breakdown(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummySect:
        is_day = True
        luminary_of_sect = "Sun"
        malefic_of_sect = "Saturn"
        benefic_of_sect = "Jupiter"
        sun_altitude_deg = 15.0

    monkeypatch.setattr(dignities_module, "sect_info", lambda *args, **kwargs: DummySect())

    houses = HousePositions(
        system="whole_sign",
        cusps=tuple(float(i * 30.0) for i in range(12)),
        ascendant=0.0,
        midheaven=90.0,
    )
    positions = {
        "Sun": BodyPosition(
            body="Sun",
            julian_day=0.0,
            longitude=19.0,
            latitude=0.0,
            distance_au=1.0,
            speed_longitude=0.95,
            speed_latitude=0.0,
            speed_distance=0.0,
            declination=0.0,
            speed_declination=0.0,
        ),
        "Saturn": BodyPosition(
            body="Saturn",
            julian_day=0.0,
            longitude=21.0,
            latitude=0.0,
            distance_au=9.5,
            speed_longitude=-0.05,
            speed_latitude=0.0,
            speed_distance=0.0,
            declination=0.0,
            speed_declination=0.0,
        ),
    }
    chart = NatalChart(
        moment=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
        location=ChartLocation(latitude=40.0, longitude=-74.0),
        julian_day=0.0,
        positions=positions,
        houses=houses,
        aspects=tuple(),
    )

    report = condition_report(chart)

    assert report["chart"]["sect"]["label"] == "day"
    assert "Sun" in report["planets"]

    sun_data = report["planets"]["Sun"]
    assert sun_data["essential"]["score"] >= 4
    assert any(
        comp.get("name") == "exaltation" and comp.get("applies") for comp in sun_data["essential"]["components"]
    )

    house_component = next(
        comp for comp in sun_data["accidental"]["components"] if comp.get("name") == "house"
    )
    assert house_component.get("quality") == "angular"

    total_sum = sum(int(info["total"]) for info in report["planets"].values())
    assert report["totals"]["overall"] == total_sum
