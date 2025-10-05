"""Tests for canonical BodyPosition normalization helpers."""

from __future__ import annotations

import pytest

from astroengine.canonical import BodyPosition


def test_body_position_wraps_longitude_into_range() -> None:
    pos = BodyPosition(lon=720.123456789, lat=0.0, dec=0.0, speed_lon=0.0)
    assert pos.lon == pytest.approx(0.12346, abs=1e-6)


def test_body_position_handles_negative_longitude() -> None:
    pos = BodyPosition(lon=-30.25, lat=0.0, dec=0.0, speed_lon=0.0)
    assert pos.lon == pytest.approx(329.75)


def test_body_position_rounds_precision() -> None:
    pos = BodyPosition(
        lon=12.3456789123,
        lat=1.23456789123,
        dec=0.123456789,
        speed_lon=0.98765432109,
    )
    assert pos.lon == pytest.approx(12.34568, abs=1e-6)
    assert pos.lat == pytest.approx(1.23457, abs=1e-6)
    assert pos.dec == pytest.approx(0.12346, abs=1e-6)
    assert pos.speed_lon == pytest.approx(0.98765, abs=1e-6)


def test_body_position_clamps_declination_upper() -> None:
    pos = BodyPosition(lon=0.0, lat=0.0, dec=95.0, speed_lon=0.0)
    assert pos.dec == 90.0


def test_body_position_clamps_declination_lower() -> None:
    pos = BodyPosition(lon=0.0, lat=0.0, dec=-95.0, speed_lon=0.0)
    assert pos.dec == -90.0


def test_body_position_handles_rounding_to_zero_longitude() -> None:
    pos = BodyPosition(lon=359.999999999, lat=0.0, dec=0.0, speed_lon=0.0)
    assert pos.lon == 0.0
