"""Overlay generation tests."""

from __future__ import annotations

from astroengine.synastry.engine import ChartPositions, Hit, make_overlay


def test_overlay_contains_wheels_and_lines() -> None:
    pos_a = ChartPositions({"Sun": 10.0, "Moon": 120.0})
    pos_b = ChartPositions({"Sun": 210.0, "Moon": 300.0})
    hit = Hit(bodyA="Sun", bodyB="Moon", aspect=90, delta=2.0, orb=6.0, severity=0.75)
    overlay = make_overlay(pos_a, pos_b, [hit])
    assert overlay.wheel_a == [("Sun", 10.0), ("Moon", 120.0)]
    assert overlay.wheel_b == [("Sun", 210.0), ("Moon", 300.0)]
    assert len(overlay.lines) == 1
    line = overlay.lines[0]
    assert line.body_a == "Sun"
    assert line.body_b == "Moon"
    assert line.aspect == 90
    assert line.offset == 2.0

