from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest

try:
    HAVE_SWISS = True
except Exception:
    HAVE_SWISS = False

SE_OK = bool(os.environ.get("SE_EPHE_PATH") or os.environ.get("SWE_EPH_PATH"))

pytestmark = pytest.mark.skipif(
    not (HAVE_SWISS and SE_OK), reason="Swiss ephemeris not available"
)

from astroengine.chart import (
    ChartLocation,
    compute_composite_chart,
    compute_harmonic_chart,
    compute_natal_chart,
    compute_return_chart,
    compute_secondary_progressed_chart,
    compute_solar_arc_chart,
)


def _sample_natal_chart() -> tuple[datetime, ChartLocation, object]:
    location = ChartLocation(latitude=40.7128, longitude=-74.0060)
    moment = datetime(1990, 1, 1, 12, tzinfo=UTC)
    chart = compute_natal_chart(moment, location)
    return moment, location, chart


def test_secondary_progressed_chart_matches_day_for_year():
    natal_moment, _, natal_chart = _sample_natal_chart()
    target = datetime(2020, 1, 1, 12, tzinfo=UTC)
    progressed = compute_secondary_progressed_chart(natal_chart, target)

    progressed_days = (
        progressed.progressed_moment - natal_moment
    ).total_seconds() / 86400.0
    expected_days = (target - natal_moment).total_seconds() / 86400.0 / 365.2422
    assert progressed_days == pytest.approx(expected_days, rel=1e-3)
    assert "Sun" in progressed.chart.positions


def test_solar_return_chart_event_metadata():
    _, location, natal_chart = _sample_natal_chart()
    return_chart = compute_return_chart(natal_chart, 2020, location=location)
    assert return_chart.event.body == "Sun"
    assert return_chart.event.method == "solar"
    assert return_chart.chart.location == location


def test_harmonic_chart_uses_natal_positions():
    _, _, natal_chart = _sample_natal_chart()
    harmonic = compute_harmonic_chart(natal_chart, 5)
    assert "Sun" in harmonic.positions
    sun_entry = harmonic.positions["Sun"]
    assert sun_entry.harmonic_longitude == pytest.approx(
        (sun_entry.base_longitude * 5) % 360.0
    )


def test_midpoint_composite_reduces_to_natal_for_identical_charts():
    _, _, natal_chart = _sample_natal_chart()
    composite = compute_composite_chart(natal_chart, natal_chart)
    assert "Sun" in composite.positions
    assert composite.positions["Sun"].midpoint_longitude == pytest.approx(
        natal_chart.positions["Sun"].longitude
    )


def test_solar_arc_chart_returns_directed_positions():
    _, _, natal_chart = _sample_natal_chart()
    target = datetime(2020, 1, 1, 12, tzinfo=UTC)
    directed = compute_solar_arc_chart(natal_chart, target)
    assert directed.arc_degrees >= 0.0
    assert "Sun" in directed.positions
