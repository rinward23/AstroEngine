import datetime as dt

import pytest

from astroengine.timeline import merge_windows, window_envelope


def test_window_envelope_converts_width_to_time():
    window = window_envelope(
        "2024-01-01T00:00:00Z",
        width_deg=2.0,
        hours_per_degree=12.0,
        metadata={"base_angle_deg": 30.0, "confidence": 0.6},
    )
    assert window.metadata["hours_per_degree"] == 12.0
    membership = window.time_membership(dt.datetime(2024, 1, 1, 6, 0, 0))
    assert 0.0 <= membership <= 1.0


def test_merge_windows_prefers_higher_confidence():
    base = window_envelope(
        "2024-01-01T00:00:00Z",
        width_deg=1.0,
        hours_per_degree=24.0,
        metadata={"confidence": 0.4},
    )
    stronger = window_envelope(
        "2024-01-01T06:00:00Z",
        width_deg=1.5,
        hours_per_degree=20.0,
        metadata={"confidence": 0.8},
    )
    merged = merge_windows([base, stronger])
    assert len(merged) == 1
    assert merged[0].confidence == pytest.approx(0.8)
    assert merged[0].metadata["hours_per_degree"] == 20.0
