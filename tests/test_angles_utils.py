from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from astroengine.core.angles import (
    AngleTracker,
    classify_relative_motion,
    normalize_degrees,
    signed_delta,
)


def test_normalize_degrees_wraps_into_range():
    assert normalize_degrees(370.0) == 10.0
    assert normalize_degrees(-10.0) == 350.0


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


def test_classify_relative_motion_states():
    applying = classify_relative_motion(121.0, 120.0, -0.5, 0.0)
    assert applying.state == "applying"

    separating = classify_relative_motion(119.0, 120.0, -0.5, 0.0)
    assert separating.state == "separating"

    stationary = classify_relative_motion(120.0, 120.0, 0.0, 0.0)
    assert stationary.state == "stationary"
