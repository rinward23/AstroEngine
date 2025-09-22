from __future__ import annotations

import math

import pytest

from astroengine.ephemeris import BodyPosition
from astroengine.esoteric import DECANS, assign_decans, decan_for_longitude


def _position(name: str, longitude: float) -> BodyPosition:
    return BodyPosition(
        body=name,
        julian_day=2451545.0,
        longitude=longitude,
        latitude=0.0,
        distance_au=1.0,
        speed_longitude=0.0,
        speed_latitude=0.0,
        speed_distance=0.0,
        declination=0.0,
        speed_declination=0.0,
    )


def test_decan_for_longitude_wraps_and_orders() -> None:
    first = decan_for_longitude(5.0)
    assert first.sign == "Aries"
    assert first.ruler == "Mars"
    assert first.tarot_card == "Two of Wands"

    wrapped = decan_for_longitude(359.5)
    assert wrapped.sign == "Pisces"
    assert wrapped.decan_index == 2
    assert wrapped.ruler == "Mars"

    second = decan_for_longitude(10.0)
    assert second.index == 1
    assert math.isclose(second.start_degree, 10.0)
    assert math.isclose(second.end_degree, 20.0)


def test_negative_longitude_normalises() -> None:
    decan = decan_for_longitude(-0.25)
    assert decan.sign == "Pisces"
    assert decan.decan_index == 2


def test_invalid_longitude_raises() -> None:
    with pytest.raises(ValueError):
        decan_for_longitude(float("nan"))


def test_assign_decans_from_body_positions() -> None:
    positions = {
        "Sun": _position("Sun", 15.0),
        "Moon": _position("Moon", 123.4),
    }
    assignments = assign_decans(positions)
    assert {a.body for a in assignments} == {"Sun", "Moon"}
    sun = next(a for a in assignments if a.body == "Sun")
    assert sun.decan.sign == "Aries"
    assert sun.decan.ruler == "Sun"
    assert sun.decan.tarot_title == "Virtue"
    moon = next(a for a in assignments if a.body == "Moon")
    assert moon.decan.sign == "Leo"
    assert moon.decan.tarot_card == "Five of Wands"


def test_assign_decans_with_iterable_input() -> None:
    iterable = [("Mercury", _position("Mercury", 60.2))]
    assignments = assign_decans(iterable)
    assert len(assignments) == 1
    assert assignments[0].decan.sign == "Gemini"
    assert assignments[0].decan.decan_index == 0


def test_decan_table_is_complete() -> None:
    assert len(DECANS) == 36
    assert DECANS[0].start_degree == 0.0
    assert DECANS[-1].end_degree == 360.0
