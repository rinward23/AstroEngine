"""Property-style tests for midpoint symmetry."""

from __future__ import annotations

import math

import pytest

from astroengine.core.rel_plus.composite import circular_midpoint


@pytest.mark.parametrize(
    "a_deg,b_deg",
    [
        (0.0, 0.0),
        (10.0, 50.0),
        (120.0, 320.0),
        (359.0, 1.0),
        (270.0, 90.0),
    ],
)
def test_midpoint_symmetric_order(a_deg: float, b_deg: float) -> None:
    mid_ab = circular_midpoint(a_deg, b_deg)
    mid_ba = circular_midpoint(b_deg, a_deg)
    delta = abs(((mid_ab - mid_ba + 180.0) % 360.0) - 180.0)
    assert math.isclose(delta, 0.0, abs_tol=1e-9) or math.isclose(delta, 180.0, abs_tol=1e-9)

