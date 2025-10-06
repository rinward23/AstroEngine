from datetime import UTC, datetime, timedelta

from core.relationship_plus.composite import (
    Geo,
    composite_positions,
    davison_midpoints,
    davison_positions,
    midpoint_angle,
)


class LinearEphemeris:
    """Synthetic ephemeris used to validate Davison positions deterministically."""

    def __init__(self, t0, base, rates):
        self.t0 = t0
        self.base = base
        self.rates = rates

    def __call__(self, ts):
        dt_days = (ts - self.t0).total_seconds() / 86400.0
        return {
            name: (self.base.get(name, 0.0) + self.rates.get(name, 0.0) * dt_days) % 360.0
            for name in self.base
        }


def test_midpoint_wrap_short_arc():
    # 350° and 10° midpoint should be 0°
    m = midpoint_angle(350.0, 10.0)
    assert abs(m - 0.0) < 1e-9
    # 10° and 190° midpoint on shortest arc is 100° (Δ=+180 pick +180 by convention → 100)
    m2 = midpoint_angle(10.0, 190.0)
    assert abs(m2 - 100.0) < 1e-9


def test_composite_positions_common_bodies():
    pos_a = {"Sun": 350.0, "Moon": 20.0, "Mars": 100.0}
    pos_b = {"Sun": 10.0, "Moon": 80.0, "Venus": 200.0}
    composite = composite_positions(pos_a, pos_b)
    assert set(composite.keys()) == {"Sun", "Moon"}
    assert abs(composite["Sun"] - 0.0) < 1e-9  # wrap midpoint


def test_davison_midpoints_and_positions():
    t0 = datetime(2025, 1, 1, tzinfo=UTC)
    a_time = t0
    b_time = t0 + timedelta(days=10)
    a_loc = Geo(10.0, 20.0)
    b_loc = Geo(-10.0, 40.0)

    mid_dt, mid_lat, mid_lon = davison_midpoints(a_time, a_loc, b_time, b_loc)
    assert mid_dt == t0 + timedelta(days=5)
    # mid lat/lon should be finite numbers
    assert abs(mid_lat) <= 90
    assert abs(mid_lon) <= 180

    eph = LinearEphemeris(
        t0,
        base={"Sun": 10.0, "Venus": 40.0},
        rates={"Sun": 1.0, "Venus": 1.2},
    )
    pos = davison_positions(eph, a_time, a_loc, b_time, b_loc, bodies=["Sun", "Venus"])
    # At mid_dt = t0+5d → Sun = 15°, Venus = 46°
    assert abs(pos["Sun"] - 15.0) < 1e-9
    assert abs(pos["Venus"] - 46.0) < 1e-9
