from __future__ import annotations

import math

import pytest

from astroengine.analysis.antiscia import antiscia
from astroengine.core.angles import normalize_degrees
from astroengine.core.rel_plus.composite import circular_midpoint

hypothesis = pytest.importorskip("hypothesis")
given = hypothesis.given
st = hypothesis.strategies
settings = hypothesis.settings

ANGLES = st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False)
INTS = st.integers(min_value=-20, max_value=20)


@settings(deadline=None)
@given(angle=ANGLES)
def test_antiscia_is_involution(angle: float) -> None:
    first = antiscia(angle)
    second = antiscia(first)
    assert math.isclose(normalize_degrees(second), normalize_degrees(angle), abs_tol=1e-9)


@settings(deadline=None)
@given(a=ANGLES, b=ANGLES)
def test_circular_midpoint_commutative(a: float, b: float) -> None:
    mid_ab = circular_midpoint(a, b)
    mid_ba = circular_midpoint(b, a)
    delta = ((mid_ab - mid_ba + 180.0) % 360.0) - 180.0
    assert math.isclose(delta, 0.0, abs_tol=1e-9)


@settings(deadline=None)
@given(angle=ANGLES, turns=INTS)
def test_normalize_degrees_wrap_invariant(angle: float, turns: int) -> None:
    shifted = normalize_degrees(angle + 360.0 * turns)
    base = normalize_degrees(angle)
    assert math.isclose(shifted, base, abs_tol=1e-9)
