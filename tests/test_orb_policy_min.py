"""Minimal smoke checks for the consolidated orb policy loader."""

from __future__ import annotations

from astroengine.scoring.orb import DEFAULT_ASPECTS, OrbCalculator


def test_defaults_present():
    required = (0, 30, 36, 40, 45, 51.4286, 60, 72, 80, 90, 102.8571, 108, 120, 135, 144, 150, 154.2857, 180)
    for angle in required:
        assert any(abs(value - angle) < 1e-3 for value in DEFAULT_ASPECTS)


def test_orb_major_vs_minor():
    calc = OrbCalculator()
    assert calc.orb_for("Sun", "Mars", 180) >= 4.0
    assert calc.orb_for("Sun", "Mars", 150) <= 2.0
