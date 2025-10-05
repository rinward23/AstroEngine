from __future__ import annotations

import math

import pytest

from astroengine.analysis.midpoints import midpoint_longitude
from astroengine.astro.declination import (
    antiscia_lon,
    available_antiscia_axes,
    contra_antiscia_lon,
)
from astroengine.core.angles import normalize_degrees, signed_delta
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
WRAPPED_FLOATS = st.floats(
    min_value=-720.0,
    max_value=720.0,
    allow_nan=False,
    allow_infinity=False,
)
AXES = st.sampled_from(available_antiscia_axes())


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


@settings(deadline=None)
@given(a=WRAPPED_FLOATS, b=WRAPPED_FLOATS)
def test_signed_delta_mirror_wrap(a: float, b: float) -> None:
    """Reflecting both angles across 360° flips the sign of the separation."""

    norm_a = normalize_degrees(a)
    norm_b = normalize_degrees(b)
    forward = signed_delta(norm_a - norm_b)
    mirrored = signed_delta((360.0 - norm_a) - (360.0 - norm_b))
    assert math.isclose(forward, -mirrored, abs_tol=1e-9)


@settings(deadline=None)
@given(a=WRAPPED_FLOATS, b=WRAPPED_FLOATS)
def test_midpoint_equidistant(a: float, b: float) -> None:
    """Midpoints remain symmetric and equidistant from both angles."""

    mid = midpoint_longitude(a, b)
    delta_a = signed_delta(mid - normalize_degrees(a))
    delta_b = signed_delta(mid - normalize_degrees(b))
    assert math.isclose(delta_a, -delta_b, abs_tol=1e-9)
    swapped = midpoint_longitude(b, a)
    assert math.isclose(((mid - swapped + 180.0) % 360.0) - 180.0, 0.0, abs_tol=1e-9)


@settings(deadline=None)
@given(angle=WRAPPED_FLOATS, axis=AXES)
def test_antiscia_is_involution(angle: float, axis: str) -> None:
    """Applying antiscia twice returns the original longitude."""

    norm = normalize_degrees(angle)
    mirrored = antiscia_lon(norm, axis=axis)
    twice = antiscia_lon(mirrored, axis=axis)
    assert math.isclose(normalize_degrees(twice), norm, abs_tol=1e-9)


@settings(deadline=None)
@given(angle=WRAPPED_FLOATS, axis=AXES)
def test_contra_antiscia_alignment(angle: float, axis: str) -> None:
    """Contra-antiscia mirrors stay exactly 180° from antiscia mirrors."""

    norm = normalize_degrees(angle)
    mirror = antiscia_lon(norm, axis=axis)
    contra = contra_antiscia_lon(norm, axis=axis)
    expected = normalize_degrees(mirror + 180.0)
    assert math.isclose(contra, expected, abs_tol=1e-9)
