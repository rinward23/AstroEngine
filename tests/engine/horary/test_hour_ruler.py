from __future__ import annotations

from datetime import UTC, datetime

import pytest

pytest.importorskip(
    "swisseph",
    reason="pyswisseph not installed; install extras with `pip install -e .[ephem,providers]`.",
)

from astroengine.engine.horary.hour_ruler import (
    GeoLocation,
    moonrise_moonset,
    planetary_hour,
)


def test_planetary_hour_midday_london() -> None:
    location = GeoLocation(latitude=51.5074, longitude=-0.1278)
    moment = datetime(2024, 3, 20, 12, 0, tzinfo=UTC)
    result = planetary_hour(moment, location)

    assert result.sunrise < result.sunset < result.next_sunrise
    assert 0 <= result.index < 12
    # 20 March 2024 is a Wednesday (Mercury day)
    assert result.day_ruler == "Mercury"


def test_planetary_hour_night_interval() -> None:
    location = GeoLocation(latitude=51.5074, longitude=-0.1278)
    moment = datetime(2024, 3, 20, 2, 0, tzinfo=UTC)
    result = planetary_hour(moment, location)

    assert result.index >= 12
    assert result.start < moment < result.end


def test_moonrise_moonset_sequence() -> None:
    location = GeoLocation(latitude=40.7128, longitude=-74.0060)
    moment = datetime(2024, 3, 20, 12, 0, tzinfo=UTC)

    moonrise, moonset, next_moonrise = moonrise_moonset(moment, location)

    assert moonrise.tzinfo is UTC
    assert moonset.tzinfo is UTC
    assert next_moonrise.tzinfo is UTC
    assert moonrise < moonset < next_moonrise
    assert moonrise <= moment <= next_moonrise
