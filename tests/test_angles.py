from __future__ import annotations

import math

import pytest

from astroengine.core.angles import signed_delta


@pytest.mark.parametrize(
    "angle, expected",
    [
        (0.0, 0.0),
        (45.0, 45.0),
        (-30.0, -30.0),
        (360.0, 0.0),
        (450.0, 90.0),
        (-450.0, -90.0),
    ],
)
def test_signed_delta_basic_wrapping(angle: float, expected: float) -> None:
    assert signed_delta(angle) == pytest.approx(expected)


@pytest.mark.parametrize(
    "angle, expected",
    [
        (180.0, -180.0),
        (-180.0, -180.0),
        (540.0, -180.0),
        (-540.0, -180.0),
    ],
)
def test_signed_delta_handles_half_turn_boundary(angle: float, expected: float) -> None:
    assert signed_delta(angle) == pytest.approx(expected)


@pytest.mark.parametrize(
    "angle, expected",
    [
        (179.999, 179.999),
        (-179.999, -179.999),
        (-180.0001, 179.9999),
        (180.0001, -179.9999),
    ],
)
def test_signed_delta_values_near_bounds(angle: float, expected: float) -> None:
    result = signed_delta(angle)
    assert -180.0 <= result < 180.0
    assert math.isclose(result, expected, rel_tol=0.0, abs_tol=1e-4)


def test_signed_delta_wraps_large_turns() -> None:
    result = signed_delta(1230.0)
    assert -180.0 <= result < 180.0
    assert result == pytest.approx(150.0, rel=0, abs=1e-9)
