from __future__ import annotations

from datetime import UTC, datetime

import pytest

pytest.importorskip(
    "swisseph",
    reason="pyswisseph not installed; install extras with `pip install -e .[ephem,providers]`.",
)

from astroengine.engine.observational.sun import solar_cycle_for_location


def test_solar_cycle_for_location_london_equinox() -> None:
    moment = datetime(2024, 3, 20, 12, 0, tzinfo=UTC)
    sunrise, sunset, next_sunrise = solar_cycle_for_location(
        moment,
        latitude_deg=51.5074,
        longitude_deg=-0.1278,
    )

    assert sunrise < sunset < next_sunrise
    assert sunrise.tzinfo is UTC
    assert sunset.tzinfo is UTC
    assert next_sunrise.tzinfo is UTC

    expected_sunrise = datetime(2024, 3, 20, 6, 1, tzinfo=UTC)
    expected_sunset = datetime(2024, 3, 20, 18, 15, tzinfo=UTC)
    expected_next = datetime(2024, 3, 21, 5, 59, tzinfo=UTC)

    assert abs((sunrise - expected_sunrise).total_seconds()) < 180
    assert abs((sunset - expected_sunset).total_seconds()) < 180
    assert abs((next_sunrise - expected_next).total_seconds()) < 240
