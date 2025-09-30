from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from astroengine.engine.progressions.mapping import (
    progressed_instant_secondary,
    progressed_instant_variant,
)


@pytest.fixture
def natal() -> datetime:
    return datetime(1990, 5, 4, 12, 30, tzinfo=UTC)


@pytest.fixture
def observation() -> datetime:
    return datetime(2025, 10, 1, 0, 0, tzinfo=UTC)


def test_secondary_progression_scales_to_one_day(natal: datetime) -> None:
    observation = natal + timedelta(days=365.242189)
    progressed = progressed_instant_secondary(natal, observation)
    delta_seconds = (progressed - natal).total_seconds()
    assert delta_seconds == pytest.approx(24 * 3600)


@pytest.mark.parametrize(
    "variant, factor",
    [
        ("day_for_month", 1.0 / 29.530588),
        ("lunar_month_for_year", 29.530588 / 365.242189),
        ("hour_for_year", 1.0 / (24.0 * 365.242189)),
    ],
)
def test_variants_apply_expected_scaling(
    natal: datetime, observation: datetime, variant: str, factor: float
) -> None:
    progressed = progressed_instant_variant(
        natal,
        observation,
        variant=variant,
    )
    delta_seconds = (progressed - natal).total_seconds()
    expected = (observation - natal).total_seconds() * factor
    assert delta_seconds == pytest.approx(expected)


def test_invalid_variant_raises(natal: datetime, observation: datetime) -> None:
    with pytest.raises(ValueError):
        progressed_instant_variant(
            natal,
            observation,
            variant="unknown",  # type: ignore[arg-type]
        )
