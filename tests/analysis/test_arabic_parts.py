from __future__ import annotations

from datetime import UTC, datetime

import pytest

from astroengine.analysis.arabic_parts import compute_all, compute_lot
from astroengine.chart.natal import ChartLocation, NatalChart
from astroengine.config.settings import ArabicPartCustom, Settings
from astroengine.ephemeris.swisseph_adapter import BodyPosition, HousePositions


def _body_position(name: str, longitude: float) -> BodyPosition:
    return BodyPosition(
        body=name,
        julian_day=0.0,
        longitude=longitude,
        latitude=0.0,
        distance_au=1.0,
        speed_longitude=0.0,
        speed_latitude=0.0,
        speed_distance=0.0,
        declination=0.0,
        speed_declination=0.0,
    )


def _test_chart() -> NatalChart:
    cusps = tuple((80.0 + 30.0 * idx) % 360.0 for idx in range(12))
    houses = HousePositions(system="placidus", cusps=cusps, ascendant=80.0, midheaven=170.0)
    positions = {
        "Sun": _body_position("Sun", 100.0),
        "Moon": _body_position("Moon", 200.0),
        "Venus": _body_position("Venus", 150.0),
    }
    return NatalChart(
        moment=datetime(2020, 1, 1, 12, tzinfo=UTC),
        location=ChartLocation(latitude=0.0, longitude=0.0),
        julian_day=0.0,
        positions=positions,
        houses=houses,
        aspects=(),
    )


def test_compute_lot_fortune_day_and_night() -> None:
    chart = _test_chart()
    asc = chart.houses.ascendant
    sun = chart.positions["Sun"].longitude
    moon = chart.positions["Moon"].longitude

    fortune_day = compute_lot("Fortune", chart, True)
    fortune_night = compute_lot("Fortune", chart, False)

    expected_day = (asc + moon - sun) % 360.0
    expected_night = (asc + sun - moon) % 360.0

    assert fortune_day == pytest.approx(expected_day)
    assert fortune_night == pytest.approx(expected_night)


def test_compute_all_uses_presets_and_custom_lots() -> None:
    chart = _test_chart()
    settings = Settings()
    settings.arabic_parts.presets.update({"Fortune": True, "Spirit": True, "Eros": False})
    settings.arabic_parts.custom = [
        ArabicPartCustom(name="MyLot", day="Lot(Fortune) + 10", night="Lot(Spirit) + 5")
    ]

    result = compute_all(settings, chart)
    assert result.is_day is True
    assert result.metadata.get("house_system") == chart.houses.system
    assert result.metadata.get("zodiac") == chart.zodiac

    lots = {item.name: item for item in result.lots}
    assert "Fortune" in lots
    assert "Spirit" in lots
    assert "MyLot" in lots
    assert lots["Fortune"].source == "preset"
    assert lots["MyLot"].source == "custom"
    assert lots["Fortune"].house == 4

    mylot_expected = (lots["Fortune"].longitude + 10.0) % 360.0
    assert lots["MyLot"].longitude == pytest.approx(mylot_expected)
