from datetime import UTC, datetime

import pytest

from astroengine.engine.lots.sect import GeoLocation, is_day


def test_is_day_equator_noon():
    moment = datetime(2023, 6, 21, 12, 0, tzinfo=UTC)
    location = GeoLocation(latitude=0.0, longitude=0.0)
    assert is_day(moment, location)


def test_is_day_equator_midnight():
    moment = datetime(2023, 6, 21, 0, 0, tzinfo=UTC)
    location = GeoLocation(latitude=0.0, longitude=0.0)
    assert not is_day(moment, location)


def test_is_day_with_override_altitude():
    moment = datetime(2023, 6, 21, 0, 0, tzinfo=UTC)
    location = GeoLocation(latitude=0.0, longitude=0.0)
    assert is_day(moment, location, sun_altitude=5.0)
    assert not is_day(moment, location, sun_altitude=-1.0)


def test_requires_timezone():
    naive = datetime(2023, 6, 21, 12, 0)
    location = GeoLocation(latitude=0.0, longitude=0.0)
    with pytest.raises(ValueError):
        is_day(naive, location)
