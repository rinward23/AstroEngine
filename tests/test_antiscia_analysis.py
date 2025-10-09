from __future__ import annotations

import math

import pytest

from astroengine.analysis.antiscia import antiscia, aspect_to_antiscia, contra_antiscia


def test_antiscia_mirror_solstitial_axis():
    assert math.isclose(antiscia(10.0), 170.0)
    assert math.isclose(antiscia(200.0), 340.0)
    assert math.isclose(antiscia(-20.0), 200.0)


def test_contra_antiscia_mirror_solstitial_axis():
    assert math.isclose(contra_antiscia(10.0), 350.0)
    assert math.isclose(contra_antiscia(200.0), 160.0)
    assert math.isclose(contra_antiscia(-45.0), 45.0)


def test_aspect_to_antiscia_matches_within_orb():
    kind, delta = aspect_to_antiscia(10.0, 171.2, 1.5)
    assert kind == "antiscia"
    assert pytest.approx(delta, rel=0, abs=1e-6) == 1.2

    kind, delta = aspect_to_antiscia(75.0, 285.25, 1.0)
    assert kind == "contra"
    assert pytest.approx(delta, rel=0, abs=1e-6) == 0.25


def test_aspect_to_antiscia_none_when_outside_orb():
    assert aspect_to_antiscia(10.0, 200.0, 1.0) is None
    assert aspect_to_antiscia(50.0, 100.0, None) is None

