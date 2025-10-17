from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from astroengine.engine.traditional.zr import (
    _build_level,
    _next_sign,
    _normalize_sign,
    apply_loosing_of_bond,
    flag_peaks_fortune,
    zr_periods,
)


def test_normalize_sign_returns_canonical_case() -> None:
    assert _normalize_sign(" aries ") == "Aries"
    with pytest.raises(ValueError):
        _normalize_sign("not-a-sign")


def test_next_sign_handles_loosing_of_bond_pairs() -> None:
    next_sign, lob = _next_sign("Cancer", None)
    assert next_sign == "Capricorn"
    assert lob == ("Cancer", "Capricorn")

    next_sign, lob = _next_sign("Capricorn", "Cancer")
    assert next_sign == "Aquarius"
    assert lob is None


def test_build_level_emits_loosing_metadata() -> None:
    start = datetime(2000, 1, 1, tzinfo=UTC)
    end = start + timedelta(days=int(50 * 365.25))
    periods = _build_level(1, start, end, "Cancer", 1)
    assert periods[0].sign == "Cancer"
    second = periods[1]
    assert second.sign == "Capricorn"
    assert second.lb and second.lb_from == "Cancer" and second.lb_to == "Capricorn"


@pytest.mark.parametrize("levels", [0, 5])
def test_zr_periods_rejects_invalid_levels(levels: int) -> None:
    start = datetime(2000, 1, 1, tzinfo=UTC)
    end = datetime(2001, 1, 1, tzinfo=UTC)
    with pytest.raises(ValueError):
        zr_periods("Aries", start, end, levels=levels)


@pytest.mark.parametrize(
    "start, end",
    [
        (datetime(2000, 1, 1), datetime(2001, 1, 1, tzinfo=UTC)),
        (datetime(2000, 1, 1, tzinfo=UTC), datetime(2000, 6, 1)),
    ],
)
def test_zr_periods_requires_timezone_awareness(start: datetime, end: datetime) -> None:
    with pytest.raises(ValueError):
        zr_periods("Aries", start, end)


def test_zr_periods_limits_levels_and_tracks_lob() -> None:
    start = datetime(2000, 1, 1, tzinfo=UTC)
    end = datetime(2030, 1, 1, tzinfo=UTC)
    timeline = zr_periods("Cancer", start, end, levels=2)
    assert set(timeline.levels) == {1, 2}
    level1 = list(timeline.levels[1])
    assert any(period.lb for period in level1)
    assert all(period.level <= 2 for period in timeline.flatten())


def test_flag_peaks_fortune_marks_major_and_moderate() -> None:
    start = datetime(2000, 1, 1, tzinfo=UTC)
    end = datetime(2125, 1, 1, tzinfo=UTC)
    timeline = zr_periods("Aries", start, end, levels=1)
    flag_peaks_fortune(timeline, "Aries")
    peaks = {period.sign: period.metadata.get("peak") for period in timeline.levels[1]}
    assert peaks.get("Aries") == "major"
    moderates = {
        sign
        for sign, value in peaks.items()
        if value == "moderate" and sign in {"Cancer", "Libra", "Capricorn"}
    }
    assert moderates, "expected cardinal modalities flagged as moderate"


def test_apply_loosing_of_bond_preserves_period_objects() -> None:
    start = datetime(2000, 1, 1, tzinfo=UTC)
    end = datetime(2010, 1, 1, tzinfo=UTC)
    timeline = zr_periods("Cancer", start, end, levels=1)
    before_level = timeline.levels[1]
    first_period = before_level[0]
    updated = apply_loosing_of_bond(timeline)
    assert updated is timeline
    assert timeline.levels[1][0] is first_period
    assert isinstance(timeline.levels[1], tuple)
