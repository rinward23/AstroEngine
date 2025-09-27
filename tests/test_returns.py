from datetime import datetime, timedelta, timezone

from astroengine.core.charts_plus.returns import (
    ReturnWindow,
    find_next_return,
    find_returns_in_window,
)


# Synthetic linear ephemeris for tests
class LinearEphemeris:
    def __init__(self, t0, base, rates):
        self.t0, self.base, self.rates = t0, base, rates

    def __call__(self, ts):
        dt_days = (ts - self.t0).total_seconds() / 86400.0
        return {
            k: (self.base[k] + self.rates.get(k, 0.0) * dt_days) % 360.0
            for k in self.base
        }


def test_solar_return_linear_rate():
    t0 = datetime(2025, 1, 1, tzinfo=timezone.utc)
    natal_lon = 10.0
    eph = LinearEphemeris(t0, base={"Sun": natal_lon}, rates={"Sun": 1.0})  # 1°/day → period 360 days

    win = ReturnWindow(start=t0 + timedelta(hours=1), end=t0 + timedelta(days=400))
    res = find_next_return("Sun", natal_lon, win, eph, step_minutes=720)  # 12h steps
    assert res is not None
    expected = t0 + timedelta(days=360)
    assert abs((res.exact_time - expected).total_seconds()) <= 60  # within 60s
    assert res.orb < 1e-6


def test_lunar_returns_multiple():
    t0 = datetime(2025, 1, 1, tzinfo=timezone.utc)
    natal_lon = 50.0
    eph = LinearEphemeris(t0, base={"Moon": natal_lon}, rates={"Moon": 13.0})  # ~27.692 days

    win = ReturnWindow(start=t0 + timedelta(hours=1), end=t0 + timedelta(days=90))
    results = find_returns_in_window("Moon", natal_lon, win, eph, step_minutes=360)  # 6h steps
    assert len(results) >= 3
    # First expected near 360/13 ≈ 27.692 days
    expected1 = t0 + timedelta(days=(360.0 / 13.0))
    assert abs((results[0].exact_time - expected1).total_seconds()) <= 60


def test_planetary_return_generic():
    t0 = datetime(2025, 1, 1, tzinfo=timezone.utc)
    natal_lon = 200.0
    eph = LinearEphemeris(t0, base={"Venus": natal_lon}, rates={"Venus": 1.2})  # period 300 days

    win = ReturnWindow(start=t0 + timedelta(hours=1), end=t0 + timedelta(days=370))
    res = find_next_return("Venus", natal_lon, win, eph, step_minutes=720)
    assert res is not None
    expected = t0 + timedelta(days=300)
    assert abs((res.exact_time - expected).total_seconds()) <= 60
