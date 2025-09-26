from __future__ import annotations

import math

import pytest

from astroengine.utils.angles import delta_angle

hypothesis = pytest.importorskip("hypothesis")
given = hypothesis.given
st = hypothesis.strategies
settings = hypothesis.settings

FLOATS = st.floats(
    min_value=-1e6,
    max_value=1e6,
    allow_nan=False,
    allow_infinity=False,
)
INTS = st.integers(min_value=-20, max_value=20)


@settings(deadline=None)
@given(a=FLOATS, b=FLOATS)
def test_delta_angle_antisymmetric(a: float, b: float) -> None:
    """delta(a, b) == -delta(b, a) within numeric tolerance."""

    forward = delta_angle(a, b)
    backward = delta_angle(b, a)
    assert math.isclose(forward, -backward, abs_tol=1e-9)


@settings(deadline=None)
@given(a=FLOATS, b=FLOATS, k=INTS, m=INTS)
def test_delta_angle_periodic(a: float, b: float, k: int, m: int) -> None:
    """Adding full turns does not change the delta."""

    shifted = delta_angle(a + 360.0 * k, b + 360.0 * m)
    base = delta_angle(a, b)
    assert math.isclose(shifted, base, abs_tol=1e-9)


@settings(deadline=None)
@given(a=FLOATS, b=FLOATS)
def test_delta_angle_range(a: float, b: float) -> None:
    """delta(a, b) stays within (-180, 180]."""

    delta = delta_angle(a, b)
    assert -180.0 < delta <= 180.0


@settings(deadline=None)
@given(a=FLOATS, b=FLOATS)
def test_delta_angle_zero_implies_congruent(a: float, b: float) -> None:
    """delta(a, b) == 0 => angles congruent modulo 360 degrees."""

    delta = delta_angle(a, b)
    if math.isclose(delta, 0.0, abs_tol=1e-9):
        congruent = math.fmod(b - a, 360.0)
        if congruent < 0.0:
            congruent += 360.0
        if congruent >= 360.0 - 1e-9:
            congruent -= 360.0
        assert math.isclose(congruent, 0.0, abs_tol=1e-9)
