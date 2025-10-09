from datetime import UTC, datetime, timedelta

from astroengine.core.aspects_plus.scan import TimeWindow, scan_pair_time_range
from tests.fixtures_ephemeris import (
    ConvergingConjunctionEphemeris,
    LinearEphemeris,
    LoopRetrogradeEphemeris,
)

POLICY = {
    "per_aspect": {"sextile": 3.0, "trine": 6.0},
    "per_object": {},
    "adaptive_rules": {},
}


def test_wraparound_sextile_detection():
    t0 = datetime(2025, 1, 1, 23, 50, tzinfo=UTC)
    eph = LinearEphemeris(
        t0,
        base={"Mars": 350.0, "Venus": 290.0},
        rates_deg_per_day={"Mars": 0.0, "Venus": 0.0},
    )
    win = TimeWindow(start=t0 - timedelta(minutes=30), end=t0 + timedelta(minutes=30))
    hits = scan_pair_time_range("Mars", "Venus", win, eph, [60.0], POLICY, step_minutes=5)
    assert any(abs(h.orb) < 1e-6 for h in hits)


def test_retrograde_loop_trine_detection():
    t0 = datetime(2025, 2, 1, tzinfo=UTC)
    t_mid = t0 + timedelta(days=10)
    eph = LoopRetrogradeEphemeris(
        t0=t0,
        base={"Jupiter": 0.0, "Saturn": 120.0},
        prograde_rates={"Jupiter": 0.8, "Saturn": 0.0},
        retrograde_rates={"Jupiter": -0.8, "Saturn": 0.0},
        t_mid=t_mid,
    )
    win = TimeWindow(start=t0, end=t0 + timedelta(days=20))
    hits = scan_pair_time_range(
        "Jupiter",
        "Saturn",
        win,
        eph,
        [120.0],
        POLICY,
        step_minutes=720,
    )
    assert len(hits) >= 1


def test_converging_conjunction_near_cazimi_window():
    t0 = datetime(2025, 3, 1, tzinfo=UTC)
    eph = ConvergingConjunctionEphemeris(
        t0=t0,
        sun_lon=0.0,
        planet_start_sep=0.5,
        planet_rate_minus_sun=-0.1,
    )
    win = TimeWindow(start=t0, end=t0 + timedelta(days=10))

    hits = scan_pair_time_range("Sun", "Mercury", win, eph, [0.0], POLICY, step_minutes=60)
    assert len(hits) >= 1

    best = min(hits, key=lambda h: h.orb)
    sep = best.orb
    assert sep < 0.2
