from datetime import datetime, timedelta, timezone

from astroengine.core.charts_plus.progressions import (
    secondary_progressed_datetime,
    secondary_progressed_positions,
    solar_arc_positions,
)


class LinearEphemeris:
    """Synthetic linear ephemeris for deterministic testing."""

    def __init__(self, t0, base, rates):
        self.t0, self.base, self.rates = t0, base, rates

    def __call__(self, ts):
        dt_days = (ts - self.t0).total_seconds() / 86400.0
        return {
            name: (self.base[name] + self.rates.get(name, 0.0) * dt_days) % 360.0
            for name in self.base
        }


def test_secondary_progressed_datetime():
    natal = datetime(2025, 1, 1, tzinfo=timezone.utc)
    target = natal + timedelta(days=365 * 30)  # ~30 years elapsed
    progressed = secondary_progressed_datetime(natal, target)

    expected = natal + timedelta(days=30)
    assert abs((progressed - expected).total_seconds()) < 86400  # within a day


def test_secondary_progressed_positions_linear():
    natal = datetime(2025, 1, 1, tzinfo=timezone.utc)
    target = natal + timedelta(days=365 * 30)
    eph = LinearEphemeris(
        natal,
        base={"Sun": 10.0, "Venus": 20.0, "Mars": 30.0},
        rates={"Sun": 1.0, "Venus": 1.2, "Mars": 0.5},
    )

    prog_dt, positions = secondary_progressed_positions(
        ["Sun", "Venus", "Mars"], natal, target, eph
    )

    assert prog_dt.tzinfo == timezone.utc

    dt_days = (prog_dt - natal).total_seconds() / 86400.0
    exp_sun = (10.0 + 1.0 * dt_days) % 360.0
    exp_venus = (20.0 + 1.2 * dt_days) % 360.0
    exp_mars = (30.0 + 0.5 * dt_days) % 360.0

    assert abs(positions["Sun"] - exp_sun) < 1e-6
    assert abs(positions["Venus"] - exp_venus) < 1e-6
    assert abs(positions["Mars"] - exp_mars) < 1e-6


def test_solar_arc_positions_linear():
    natal = datetime(2025, 1, 1, tzinfo=timezone.utc)
    target = natal + timedelta(days=365 * 30)
    eph = LinearEphemeris(
        natal,
        base={"Sun": 10.0, "Venus": 20.0, "Mars": 30.0},
        rates={"Sun": 1.0, "Venus": 1.2, "Mars": 0.5},
    )

    arc, positions = solar_arc_positions(["Sun", "Venus", "Mars"], natal, target, eph)

    dt_days = (secondary_progressed_datetime(natal, target) - natal).total_seconds() / 86400.0
    exp_arc = (1.0 * dt_days) % 360.0

    assert abs(arc - exp_arc) < 1e-6
    assert abs(positions["Sun"] - ((10.0 + exp_arc) % 360.0)) < 1e-6
    assert abs(positions["Venus"] - ((20.0 + exp_arc) % 360.0)) < 1e-6
    assert abs(positions["Mars"] - ((30.0 + exp_arc) % 360.0)) < 1e-6
