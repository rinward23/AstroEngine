from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from astroengine.chart.natal import ChartLocation, NatalChart
import astroengine.engine.horary.aspects_logic as aspects_logic
from astroengine.engine.horary.aspects_logic import find_collection, find_translation
from astroengine.engine.horary.models import AspectContact
from astroengine.engine.horary.profiles import HoraryProfile
from astroengine.engine.horary.rulers import dignities_at, house_ruler, reception_for
from astroengine.ephemeris.swisseph_adapter import BodyPosition, HousePositions


_DEF_ORBS = {
    "by_aspect": {
        "conjunction": 8.0,
        "sextile": 6.0,
        "square": 6.0,
        "trine": 6.0,
        "opposition": 8.0,
    }
}


def _profile(name: str = "Tables") -> HoraryProfile:
    return HoraryProfile(
        name=name,
        orbs=_DEF_ORBS,
        dignities={
            "domicile": 5.0,
            "exaltation": 4.0,
            "triplicity": 3.0,
            "term": 2.0,
            "face": 1.0,
            "detriment": -5.0,
            "fall": -4.0,
        },
        radicality={},
        testimony_weights={},
        classification_thresholds={},
    )


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


def _chart(positions: dict[str, BodyPosition]) -> NatalChart:
    houses = HousePositions(
        system="P",
        cusps=tuple(float(i * 30) for i in range(12)),
        ascendant=0.0,
        midheaven=90.0,
    )
    return NatalChart(
        moment=datetime(2024, 3, 21, 12, tzinfo=UTC),
        location=ChartLocation(latitude=0.0, longitude=0.0),
        julian_day=0.0,
        positions=positions,
        houses=houses,
        aspects=(),
    )


def test_house_ruler_numeric_and_longitude_inputs() -> None:
    assert house_ruler("Aries") == "Mars"
    assert house_ruler(4) == "Moon"
    assert house_ruler(75.0) == "Mercury"


def test_dignity_scoring_and_reception() -> None:
    profile = _profile()
    status = dignities_at("Mars", 15.0, profile=profile, is_day_chart=True)
    assert status.domicile == "Mars"
    assert status.score == pytest.approx(5.0)
    receptions = reception_for("Sun", status)
    assert "domicile" in receptions


def test_aspect_helpers_translation_and_collection(monkeypatch) -> None:
    profile = _profile("Aspects")
    positions = {
        "Venus": _body("Venus", 20.0, 1.0),
        "Mars": _body("Mars", 76.0, 0.6),
        "Moon": _body("Moon", 18.0, 12.5),
        "Saturn": _body("Saturn", 358.0, 0.04),
    }
    chart = _chart(positions)

    original = aspects_logic.aspect_between

    def _mock_aspect_between(chart, body_a, body_b, prof):
        pair = (body_a, body_b)
        if pair == ("Moon", "Venus") or pair == ("Venus", "Moon"):
            return AspectContact(
                body_a=body_a,
                body_b=body_b,
                aspect="trine",
                orb=1.0,
                exact_delta=0.0,
                applying=False,
                moving_body="Moon",
                target_longitude=0.0,
                perfection_time=None,
            )
        if pair == ("Moon", "Mars") or pair == ("Mars", "Moon"):
            return AspectContact(
                body_a=body_a,
                body_b=body_b,
                aspect="trine",
                orb=0.5,
                exact_delta=0.0,
                applying=True,
                moving_body="Moon",
                target_longitude=0.0,
                perfection_time=chart.moment + timedelta(days=5),
            )
        if pair == ("Saturn", "Venus") or pair == ("Venus", "Saturn"):
            return AspectContact(
                body_a=body_a,
                body_b=body_b,
                aspect="sextile",
                orb=0.3,
                exact_delta=0.0,
                applying=True,
                moving_body="Venus",
                target_longitude=0.0,
                perfection_time=chart.moment + timedelta(days=10),
            )
        if pair == ("Saturn", "Mars") or pair == ("Mars", "Saturn"):
            return AspectContact(
                body_a=body_a,
                body_b=body_b,
                aspect="sextile",
                orb=0.2,
                exact_delta=0.0,
                applying=True,
                moving_body="Mars",
                target_longitude=0.0,
                perfection_time=chart.moment + timedelta(days=12),
            )
        return original(chart, body_a, body_b, prof)

    monkeypatch.setattr(aspects_logic, "aspect_between", _mock_aspect_between)

    translation = find_translation(chart, "Venus", "Mars", profile, window_days=20.0)
    assert translation is not None
    assert translation.translator == "Moon"
    assert translation.sequence[0].applying is False
    assert translation.sequence[1].applying is True

    collection = find_collection(chart, "Venus", "Mars", profile, window_days=30.0)
    assert collection is not None
    assert collection.collector == "Saturn"
    assert all(contact.applying for contact in collection.sequence)
