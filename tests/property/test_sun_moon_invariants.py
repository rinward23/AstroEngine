from __future__ import annotations

import datetime as dt
import math

import pytest

pytestmark = pytest.mark.swiss

try:
    from astroengine.engine.returns._codes import resolve_body_code
    from astroengine.utils.angles import norm360
    from astroengine.ephemeris import EphemerisAdapter
except ImportError as exc:  # pragma: no cover - optional dependency gating
    pytest.skip(f"Ephemeris adapter unavailable: {exc}", allow_module_level=True)
    resolve_body_code = lambda name: None  # type: ignore[assignment]
    norm360 = lambda value: value  # type: ignore[assignment]
    EphemerisAdapter = None  # type: ignore[assignment]
    _EPHEMERIS_IMPORT_ERROR = exc
else:
    _EPHEMERIS_IMPORT_ERROR = None

hypothesis = pytest.importorskip("hypothesis")

given = hypothesis.given
settings = hypothesis.settings
st = hypothesis.strategies

UTC = dt.UTC

MOMENTS = st.datetimes(
    min_value=dt.datetime(1950, 1, 1, tzinfo=UTC),
    max_value=dt.datetime(2050, 12, 31, 23, 59, 59, tzinfo=UTC),
    timezones=st.just(UTC),
)

if EphemerisAdapter is None:  # pragma: no cover - depends on optional deps
    pytest.skip(f"EphemerisAdapter unavailable: {_EPHEMERIS_IMPORT_ERROR}")

ADAPTER = EphemerisAdapter()


def _forward_diff(a: float, b: float) -> float:
    """Return the forward angular difference from ``a`` to ``b`` in degrees."""

    return math.fmod(b - a, 360.0) % 360.0


@settings(deadline=None, max_examples=64)
@given(moment=MOMENTS)
def test_solar_lunar_longitude_latitude_ranges(moment: dt.datetime) -> None:
    """Sun/Moon samples remain within expected ecliptic ranges."""

    for body in (SUN_CODE, MOON_CODE):
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
    base = norm360(float(ADAPTER.sample(SUN_CODE, start).longitude))
    later = norm360(float(ADAPTER.sample(SUN_CODE, end).longitude))
    diff = _forward_diff(base, later)
    assert diff >= -1e-6
    assert diff <= 1.0 + 1e-6


@settings(deadline=None, max_examples=48)
@given(moment=MOMENTS, minutes=st.integers(min_value=1, max_value=180))
def test_moon_progresses_without_retrograde(moment: dt.datetime, minutes: int) -> None:
    """The Moon's ecliptic longitude advances across small deltas."""

    end = moment + dt.timedelta(minutes=minutes)
    base = norm360(float(ADAPTER.sample(MOON_CODE, moment).longitude))
    later = norm360(float(ADAPTER.sample(MOON_CODE, end).longitude))
    diff = _forward_diff(base, later)
    assert diff >= -1e-6
    assert diff <= 2.0 + 1e-6
SUN_CODE = resolve_body_code("Sun").code
MOON_CODE = resolve_body_code("Moon").code
