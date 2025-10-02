from __future__ import annotations

from datetime import UTC, datetime

from astroengine.chart.natal import ChartLocation, NatalChart
from astroengine.engine.horary.hour_ruler import PlanetaryHourResult
from astroengine.engine.horary.models import DignityStatus, Significator, SignificatorSet
from astroengine.engine.horary.profiles import get_profile
from astroengine.engine.horary.radicality import run_checks
from astroengine.ephemeris.swisseph_adapter import BodyPosition, HousePositions


def _body(name: str, longitude: float, speed: float) -> BodyPosition:
    return BodyPosition(
        body=name,
        julian_day=0.0,
        longitude=longitude,
        latitude=0.0,
        distance_au=1.0,
        speed_longitude=speed,
        speed_latitude=0.0,
        speed_distance=0.0,
        declination=0.0,
        speed_declination=0.0,
    )


def _significator(body: str, longitude: float, house: int) -> Significator:
    return Significator(
        body=body,
        role=f"{body.lower()}_role",
        longitude=longitude,
        latitude=0.0,
        speed=0.5,
        house=house,
        dignities=DignityStatus(score=2.0),
        receptions={},
    )


def test_early_ascendant_and_saturn_warning() -> None:
    houses = HousePositions(
        system="P",
        cusps=tuple(float(i * 30) for i in range(12)),
        ascendant=1.5,
        midheaven=90.0,
    )
    positions = {
        "Moon": _body("Moon", 15.0, 12.0),
        "Saturn": _body("Saturn", 190.0, 0.04),
        "Sun": _body("Sun", 10.0, 1.0),
        "True Node": _body("True Node", 181.0, -0.05),
    }
    chart = NatalChart(
        moment=datetime(2024, 1, 1, tzinfo=UTC),
        location=ChartLocation(latitude=0.0, longitude=0.0),
        julian_day=0.0,
        positions=positions,
        houses=houses,
        aspects=(),
    )
    hour = PlanetaryHourResult(
        ruler="Jupiter",
        index=3,
        start=datetime(2024, 1, 1, 1, 0, tzinfo=UTC),
        end=datetime(2024, 1, 1, 2, 0, tzinfo=UTC),
        sunrise=datetime(2024, 1, 1, 0, 30, tzinfo=UTC),
        sunset=datetime(2024, 1, 1, 11, 0, tzinfo=UTC),
        next_sunrise=datetime(2024, 1, 2, 0, 30, tzinfo=UTC),
        day_ruler="Sun",
        sequence=("Jupiter",) * 24,
    )
    sigset = SignificatorSet(
        querent=_significator("Mars", 5.0, 1),
        quesited=_significator("Venus", 200.0, 7),
        moon=_significator("Moon", 15.0, 3),
        co_significators=(),
        is_day_chart=True,
    )
    profile = get_profile("Lilly")

    checks = run_checks(chart, profile, sigset, hour)
    codes = {check.code for check in checks if check.flag}
    assert "asc_early" in codes
    assert "saturn_in_7th" in codes
    assert "south_node_asc" in codes
