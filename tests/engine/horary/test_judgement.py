from __future__ import annotations

from datetime import UTC, datetime

from astroengine.chart.natal import ChartLocation, NatalChart
from astroengine.engine.horary.judgement import score_testimonies
from astroengine.engine.horary.models import (
    DignityStatus,
    RadicalityCheck,
    Significator,
    SignificatorSet,
)
from astroengine.engine.horary.profiles import get_profile
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


def _chart() -> NatalChart:
    positions = {
        "Venus": _body("Venus", 20.0, 1.0),
        "Mars": _body("Mars", 80.0, 0.6),
        "Moon": _body("Moon", 28.0, 12.5),
    }
    houses = HousePositions(
        system="P",
        cusps=tuple(float(i * 30) for i in range(12)),
        ascendant=0.0,
        midheaven=90.0,
    )
    return NatalChart(
        moment=datetime(2024, 1, 1, tzinfo=UTC),
        location=ChartLocation(latitude=0.0, longitude=0.0),
        julian_day=0.0,
        positions=positions,
        houses=houses,
        aspects=(),
    )


def _sigset() -> SignificatorSet:
    querent = Significator(
        body="Venus",
        role="querent_ruler",
        longitude=20.0,
        latitude=0.0,
        speed=1.0,
        house=1,
        dignities=DignityStatus(domicile="Venus", score=5.0),
        receptions={},
    )
    quesited = Significator(
        body="Mars",
        role="quesited_ruler",
        longitude=80.0,
        latitude=0.0,
        speed=0.6,
        house=10,
        dignities=DignityStatus(score=1.0),
        receptions={},
    )
    moon = Significator(
        body="Moon",
        role="moon",
        longitude=28.0,
        latitude=0.0,
        speed=12.5,
        house=3,
        dignities=DignityStatus(score=0.0),
        receptions={},
    )
    return SignificatorSet(
        querent=querent,
        quesited=quesited,
        moon=moon,
        co_significators=(),
        is_day_chart=True,
    )


def test_judgement_scoring_and_penalty() -> None:
    chart = _chart()
    sigset = _sigset()
    profile = get_profile("Lilly")

    result = score_testimonies(chart, sigset, [], profile)
    assert result.classification in {"Yes", "Qualified", "Weak", "No"}

    penalty = RadicalityCheck(
        code="penalty",
        flag=True,
        reason="Test penalty",
        caution_weight=-10.0,
        data={},
    )
    penalized = score_testimonies(chart, sigset, [penalty], profile)
    assert penalized.score < result.score

