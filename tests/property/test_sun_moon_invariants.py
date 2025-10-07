from __future__ import annotations

import datetime as dt
import math

import pytest

from astroengine.ephemeris import EphemerisAdapter
from astroengine.utils.angles import norm360

hypothesis = pytest.importorskip("hypothesis")
_swe = pytest.importorskip("swisseph")

given = hypothesis.given
settings = hypothesis.settings
st = hypothesis.strategies

UTC = dt.UTC

MOMENTS = st.datetimes(
    min_value=dt.datetime(1950, 1, 1, tzinfo=UTC),
    max_value=dt.datetime(2050, 12, 31, 23, 59, 59, tzinfo=UTC),
    timezones=st.just(UTC),
)

ADAPTER = EphemerisAdapter()


def _forward_diff(a: float, b: float) -> float:
    """Return the forward angular difference from ``a`` to ``b`` in degrees."""

    return math.fmod(b - a, 360.0) % 360.0


@settings(deadline=None, max_examples=64)
@given(moment=MOMENTS)
def test_solar_lunar_longitude_latitude_ranges(moment: dt.datetime) -> None:
    """Sun/Moon samples remain within expected ecliptic ranges."""

    for body in (_swe.SUN, _swe.MOON):
        sample = ADAPTER.sample(body, moment)
        lon = norm360(float(sample.longitude))
        lat = float(sample.latitude)
        assert 0.0 <= lon < 360.0
        assert -90.0 <= lat <= 90.0


@settings(deadline=None, max_examples=48)
@given(moment=MOMENTS, minutes=st.integers(min_value=1, max_value=120))
def test_sun_monotonic_over_short_intervals(moment: dt.datetime, minutes: int) -> None:
    """The Sun's apparent longitude increases steadily over short time spans."""

    start = moment
    end = moment + dt.timedelta(minutes=minutes)
    base = norm360(float(ADAPTER.sample(_swe.SUN, start).longitude))
    later = norm360(float(ADAPTER.sample(_swe.SUN, end).longitude))
    diff = _forward_diff(base, later)
    assert diff >= -1e-6
    assert diff <= 1.0 + 1e-6


@settings(deadline=None, max_examples=48)
@given(moment=MOMENTS, minutes=st.integers(min_value=1, max_value=180))
def test_moon_progresses_without_retrograde(moment: dt.datetime, minutes: int) -> None:
    """The Moon's ecliptic longitude advances across small deltas."""

    end = moment + dt.timedelta(minutes=minutes)
    base = norm360(float(ADAPTER.sample(_swe.MOON, moment).longitude))
    later = norm360(float(ADAPTER.sample(_swe.MOON, end).longitude))
    diff = _forward_diff(base, later)
    assert diff >= -1e-6
    assert diff <= 2.0 + 1e-6
