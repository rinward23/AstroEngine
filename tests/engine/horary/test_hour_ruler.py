from __future__ import annotations

from datetime import UTC, datetime

from astroengine.engine.horary.hour_ruler import GeoLocation, planetary_hour


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

