from __future__ import annotations

import pytest

hypothesis = pytest.importorskip("hypothesis")
given = hypothesis.given
settings = hypothesis.settings
st = hypothesis.strategies
assume = hypothesis.assume

from astroengine.core.angles import (
    AngleTracker,
    classify_relative_motion,
    normalize_degrees,
    signed_delta,
)


def test_normalize_degrees_wraps_into_range():
    assert normalize_degrees(370.0) == 10.0
    assert normalize_degrees(-10.0) == 350.0


@given(st.floats(-1e6, 1e6, allow_nan=False, allow_infinity=False))
def test_normalize_degrees_range(angle: float) -> None:
    wrapped = normalize_degrees(angle)
    assert 0.0 <= wrapped < 360.0


@given(
    st.floats(-1e6, 1e6, allow_nan=False, allow_infinity=False),
    st.integers(-5, 5),
)
def test_normalize_degrees_turn_invariance(angle: float, turns: int) -> None:
    shifted = angle + turns * 360.0
    assert normalize_degrees(angle) == pytest.approx(normalize_degrees(shifted))


def test_signed_delta_produces_expected_range():
    assert -180.0 <= signed_delta(-720.0) < 180.0
    assert -180.0 <= signed_delta(720.0) < 180.0


def test_angle_tracker_continuity():
    tracker = AngleTracker()
    values = [359.0, 1.0, 2.0]
    outputs = [tracker.update(v) for v in values]
    assert outputs[1] > outputs[0]
    assert outputs[2] > outputs[1]


@given(st.floats(-720.0, 720.0))
def test_signed_delta_property(angle: float) -> None:
    wrapped = signed_delta(angle)
    assert -180.0 <= wrapped < 180.0


@settings(deadline=None)
@given(st.floats(-1e6, 1e6))
def test_normalize_degrees_periodicity(angle: float) -> None:
    wrapped = normalize_degrees(angle)
    wrapped_shifted = normalize_degrees(angle + 360.0)
    assert wrapped == pytest.approx(wrapped_shifted)


@given(
    st.floats(-360.0, 360.0, allow_nan=False, allow_infinity=False),
    st.floats(-360.0, 360.0, allow_nan=False, allow_infinity=False),
    st.floats(-5.0, 5.0, allow_nan=False, allow_infinity=False),
    st.floats(-5.0, 5.0, allow_nan=False, allow_infinity=False),
)
def test_classify_relative_motion_sign_consistency(
    separation: float, aspect: float, moving_speed: float, reference_speed: float
) -> None:
    motion = classify_relative_motion(
        separation, aspect, moving_speed, reference_speed, tolerance=0.0
    )

    offset = separation - aspect
    relative_speed = moving_speed - reference_speed
    assume(abs(offset) > 1e-6)
    assume(abs(relative_speed) > 1e-6)

    expected = "applying" if offset * relative_speed < 0 else "separating"
    assert motion.state == expected
    assert motion.is_applying == (expected == "applying")
    assert motion.is_separating == (expected == "separating")


def test_classify_relative_motion_states():
    applying = classify_relative_motion(121.0, 120.0, -0.5, 0.0)
    assert applying.state == "applying"

    separating = classify_relative_motion(119.0, 120.0, -0.5, 0.0)
    assert separating.state == "separating"

    stationary = classify_relative_motion(120.0, 120.0, 0.0, 0.0)
    assert stationary.state == "stationary"
