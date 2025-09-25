from __future__ import annotations

import datetime as dt
from math import comb

import pytest

from astroengine.chart import (
    ChartLocation,
    compute_composite_chart,
    compute_midpoint_tree,
    compute_natal_chart,
)

NYC_MOMENT = dt.datetime(
    1990, 2, 16, 13, 30, tzinfo=dt.timezone(dt.timedelta(hours=-5))
)
NYC_LOCATION = ChartLocation(latitude=40.7128, longitude=-74.0060)

LONDON_MOMENT = dt.datetime(
    1985, 7, 13, 17, 45, tzinfo=dt.timezone(dt.timedelta(hours=1))
)
LONDON_LOCATION = ChartLocation(latitude=51.5074, longitude=-0.1278)


@pytest.mark.swiss
def test_midpoint_composite_matches_expected() -> None:
    chart_a = compute_natal_chart(NYC_MOMENT, NYC_LOCATION)
    chart_b = compute_natal_chart(LONDON_MOMENT, LONDON_LOCATION)

    composite = compute_composite_chart(chart_a, chart_b)

    assert composite.method == "midpoint"
    assert composite.sources == (chart_a, chart_b)
    assert composite.location.latitude == pytest.approx(46.1101, abs=1e-4)
    assert composite.location.longitude == pytest.approx(-37.0669, abs=1e-4)

    expected_jd = (chart_a.julian_day + chart_b.julian_day) / 2.0
    assert composite.julian_day == pytest.approx(expected_jd, abs=1e-6)

    assert composite.positions["Sun"].longitude == pytest.approx(39.5202865, abs=1e-6)
    assert composite.positions["Moon"].longitude == pytest.approx(143.998464, abs=1e-6)
    assert composite.houses.ascendant == pytest.approx(172.9356859, abs=1e-6)
    assert composite.houses.midheaven == pytest.approx(265.9822919, abs=1e-6)

    expected_midpoint_count = comb(len(composite.positions), 2)
    assert len(composite.midpoints) == expected_midpoint_count
    sun_moon = next(entry for entry in composite.midpoints if entry.name == "Sun/Moon")
    assert sun_moon.position.longitude == pytest.approx(91.75937525, abs=1e-6)
    assert sun_moon.separation == pytest.approx(104.4781775, abs=1e-6)


@pytest.mark.swiss
def test_midpoint_tree_for_natal_chart() -> None:
    chart = compute_natal_chart(NYC_MOMENT, NYC_LOCATION)
    tree = compute_midpoint_tree(chart)

    assert len(tree) == comb(len(chart.positions), 2)

    sun = chart.positions["Sun"]
    moon = chart.positions["Moon"]
    sun_moon = next(entry for entry in tree if entry.name == "Sun/Moon")
    assert sun_moon.position.longitude == pytest.approx(277.3186165, abs=1e-6)
    assert sun_moon.separation == pytest.approx(101.012701, abs=1e-6)
    assert sun_moon.position.latitude == pytest.approx(
        (sun.latitude + moon.latitude) / 2.0, abs=1e-6
    )
    assert sun_moon.position.declination == pytest.approx(
        (sun.declination + moon.declination) / 2.0, abs=1e-6
    )


@pytest.mark.swiss
def test_davison_composite_matches_direct_chart() -> None:
    chart_a = compute_natal_chart(NYC_MOMENT, NYC_LOCATION)
    chart_b = compute_natal_chart(LONDON_MOMENT, LONDON_LOCATION)

    midpoint = compute_composite_chart(chart_a, chart_b)
    davison = compute_composite_chart(chart_a, chart_b, method="davison")

    assert davison.method == "davison"
    assert davison.moment == midpoint.moment
    assert davison.location == midpoint.location

    expected = compute_natal_chart(davison.moment, davison.location)
    assert davison.positions["Sun"].longitude == pytest.approx(
        expected.positions["Sun"].longitude, abs=1e-6
    )
    assert davison.positions["Moon"].longitude == pytest.approx(
        expected.positions["Moon"].longitude, abs=1e-6
    )
