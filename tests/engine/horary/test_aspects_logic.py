from __future__ import annotations

from datetime import UTC, datetime

from astroengine.chart.natal import ChartLocation, NatalChart
from astroengine.engine.horary.aspects_logic import (
    aspect_between,
    find_collection,
    find_prohibition,
    find_translation,
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


def _chart_for_positions(mapping: dict[str, tuple[float, float]]) -> NatalChart:
    positions = {
        name: _body(name, lon, speed) for name, (lon, speed) in mapping.items()
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


def test_aspect_between_detects_applying_sextile() -> None:
    chart = _chart_for_positions(
        {
            "Venus": (20.0, 1.0),
            "Mars": (76.0, 0.6),
        }
    )
    profile = get_profile("Lilly")
    contact = aspect_between(chart, "Venus", "Mars", profile)
    assert contact is not None
    assert contact.aspect == "sextile"
    assert contact.applying


def test_translation_of_light_identified() -> None:
    chart = _chart_for_positions(
        {
            "Venus": (20.0, 1.0),
            "Mars": (76.0, 0.6),
            "Moon": (18.0, 12.5),
        }
    )
    profile = get_profile("Lilly")
    translation = find_translation(chart, "Venus", "Mars", profile, window_days=10.0)
    assert translation is not None
    assert translation.translator == "Moon"


def test_collection_absent_when_no_common_applications() -> None:
    chart = _chart_for_positions(
        {
            "Venus": (10.0, 1.0),
            "Mars": (190.0, 0.7),
            "Saturn": (120.0, 0.05),
        }
    )
    profile = get_profile("Lilly")
    collection = find_collection(chart, "Venus", "Mars", profile, window_days=10.0)
    assert collection is None


def test_prohibition_detected_before_perfection() -> None:
    chart = _chart_for_positions(
        {
            "Venus": (10.0, 1.0),
            "Mars": (70.0, 0.8),
            "Mercury": (40.0, 1.2),
        }
    )
    profile = get_profile("Lilly")
    prohibition = find_prohibition(chart, "Venus", "Mars", profile, window_days=10.0)
    assert prohibition is None
