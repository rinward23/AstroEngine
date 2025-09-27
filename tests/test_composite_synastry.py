"""Tests for composite, Davison, and synastry helpers."""

from datetime import datetime, timedelta, timezone

from astroengine.core.rel_plus.composite import (
    circular_midpoint,
    composite_midpoint_positions,
    davison_positions,
)
from astroengine.core.rel_plus.synastry import synastry_grid, synastry_interaspects


class LinearEphemeris:
    """Simple linear ephemeris for deterministic testing."""

    def __init__(self, t0, base, rates):
        self.t0 = t0
        self.base = base
        self.rates = rates

    def __call__(self, ts):
        dt_days = (ts - self.t0).total_seconds() / 86400.0
        return {
            key: (self.base.get(key, 0.0) + self.rates.get(key, 0.0) * dt_days) % 360.0
            for key in self.base
        }


POLICY = {
    "per_object": {},
    "per_aspect": {
        "sextile": 3.0,
        "trine": 6.0,
        "square": 6.0,
        "conjunction": 8.0,
    },
    "adaptive_rules": {},
}


def test_circular_midpoint_wrap():
    assert abs(circular_midpoint(350.0, 10.0) - 0.0) < 1e-9
    assert abs(circular_midpoint(10.0, 350.0) - 0.0) < 1e-9


def test_composite_midpoint_positions():
    pos_a = {"Sun": 10.0, "Moon": 200.0}
    pos_b = {"Sun": 50.0, "Moon": 220.0}
    out = composite_midpoint_positions(pos_a, pos_b, ["Sun", "Moon", "Mars"])
    assert abs(out["Sun"] - 30.0) < 1e-9
    assert abs(out["Moon"] - 210.0) < 1e-9


def test_davison_positions_time_midpoint():
    t0 = datetime(2025, 1, 1, tzinfo=timezone.utc)
    t1 = t0 + timedelta(days=10)
    eph = LinearEphemeris(
        t0,
        base={"Sun": 0.0, "Venus": 20.0},
        rates={"Sun": 1.0, "Venus": 1.2},
    )
    pos = davison_positions(["Sun", "Venus"], t0, t1, eph)
    assert abs(pos["Sun"] - 5.0) < 1e-9
    assert abs(pos["Venus"] - (20.0 + 6.0)) < 1e-9


def test_synastry_interaspects_and_grid():
    pos_a = {"Mars": 10.0, "Sun": 0.0}
    pos_b = {"Venus": 70.0, "Moon": 180.0}

    hits = synastry_interaspects(
        pos_a,
        pos_b,
        ["sextile", "trine", "square", "conjunction"],
        POLICY,
    )
    assert any(
        hit["a_obj"] == "Mars"
        and hit["b_obj"] == "Venus"
        and hit["aspect"] == "sextile"
        for hit in hits
    )

    grid = synastry_grid(hits)
    assert grid["Mars"]["Venus"] == 1
