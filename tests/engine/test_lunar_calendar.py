from __future__ import annotations

import math

import pytest

from astroengine.engine.lunar import MASA_SEQUENCE, masa_for_longitude, paksha_from_longitudes


@pytest.mark.parametrize(
    "sun, expected_name",
    [
        (0.0, MASA_SEQUENCE[0]),
        (45.0, MASA_SEQUENCE[1]),
        (215.0, MASA_SEQUENCE[7]),
        (359.9, MASA_SEQUENCE[11]),
    ],
)
def test_masa_matches_solar_sign(sun: float, expected_name: str) -> None:
    info = masa_for_longitude(sun, zodiac="sidereal")
    assert info.name == expected_name
    assert math.isclose(info.longitude, sun % 360.0)


def test_masa_marks_requested_zodiac() -> None:
    tropical = masa_for_longitude(75.0, zodiac="tropical")
    sidereal = masa_for_longitude(75.0, zodiac="sidereal")
    assert tropical.zodiac == "tropical"
    assert sidereal.zodiac == "sidereal"
    assert tropical.name == sidereal.name == MASA_SEQUENCE[2]


def test_paksha_shukla_sequence() -> None:
    info = paksha_from_longitudes(moon_longitude=5.0, sun_longitude=0.0)
    assert info.name == "Shukla"
    assert info.waxing is True
    assert info.tithi_index == 1
    assert info.tithi_name == "Pratipada"
    assert info.day_in_paksha == 1


def test_paksha_krishna_sequence() -> None:
    info = paksha_from_longitudes(moon_longitude=350.0, sun_longitude=10.0)
    assert info.name == "Krishna"
    assert info.waxing is False
    assert info.tithi_index == 29
    assert info.tithi_name == "Chaturdashi"
    assert info.day_in_paksha == 14


def test_paksha_handles_amavasya_boundary() -> None:
    info = paksha_from_longitudes(moon_longitude=359.99, sun_longitude=0.0)
    assert info.tithi_index == 30
    assert info.tithi_name == "Amavasya"
    assert info.day_in_paksha == 15
