from datetime import UTC, datetime

import pytest

from astroengine.engine.lots import ChartContext, ChartLocation, builtin_profile, evaluate


def _chart_context(positions: dict[str, float], *, is_day: bool) -> ChartContext:
    location = ChartLocation(latitude=0.0, longitude=0.0)
    return ChartContext(
        moment=datetime(2020, 1, 1, tzinfo=UTC),
        location=location,
        positions=positions,
        angles={"ASC": positions["ASC"]},
        is_day_override=is_day,
    )


def test_fortune_day_formula():
    profile = builtin_profile("Hellenistic").compile()
    positions = {
        "Sun": 100.0,
        "Moon": 10.0,
        "ASC": 50.0,
        "Mercury": 30.0,
        "Venus": 80.0,
        "Mars": 150.0,
        "Jupiter": 200.0,
        "Saturn": 250.0,
    }
    ctx = _chart_context(positions, is_day=True)
    values = evaluate(profile, ctx)
    assert pytest.approx(values["Fortune"], rel=1e-6) == 320.0
    assert pytest.approx(values["Spirit"], rel=1e-6) == 140.0


def test_fortune_night_formula():
    profile = builtin_profile("Hellenistic").compile()
    positions = {
        "Sun": 100.0,
        "Moon": 10.0,
        "ASC": 50.0,
        "Mercury": 30.0,
        "Venus": 80.0,
        "Mars": 150.0,
        "Jupiter": 200.0,
        "Saturn": 250.0,
    }
    ctx = _chart_context(positions, is_day=False)
    values = evaluate(profile, ctx)
    assert pytest.approx(values["Fortune"], rel=1e-6) == 140.0
    assert pytest.approx(values["Spirit"], rel=1e-6) == 320.0
