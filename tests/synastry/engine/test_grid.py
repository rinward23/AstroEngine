"""Grid selection logic tests."""

from __future__ import annotations

from astroengine.synastry.engine import Hit, build_grid


def test_grid_prefers_major_on_tie() -> None:
    hit_major = Hit(bodyA="Sun", bodyB="Moon", aspect=120, delta=2.0, orb=6.0, severity=0.9)
    hit_minor = Hit(bodyA="Sun", bodyB="Moon", aspect=30, delta=1.0, orb=2.0, severity=0.9)
    grid = build_grid([hit_minor, hit_major], ["Sun"], ["Moon"])
    assert grid["Sun"]["Moon"].best == hit_major


def test_empty_cell_when_no_hit() -> None:
    grid = build_grid([], ["Sun"], ["Moon"])
    assert grid["Sun"]["Moon"].best is None

