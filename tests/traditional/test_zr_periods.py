from __future__ import annotations

from datetime import UTC, datetime

from astroengine.engine.traditional import apply_loosing_of_bond, flag_peaks_fortune, zr_periods


def test_zodiacal_releasing_l1_sequences_with_lob() -> None:
    start = datetime(2000, 1, 1, tzinfo=UTC)
    end = datetime(2035, 1, 1, tzinfo=UTC)
    timeline = zr_periods("Cancer", start, end, levels=2)
    timeline = apply_loosing_of_bond(timeline)
    level1 = list(timeline.levels[1])
    assert level1[0].sign == "Cancer"
    span_years = (level1[0].end - level1[0].start).total_seconds() / 86400.0 / 365.2425
    assert 24.5 < span_years < 25.5
    assert level1[1].sign == "Capricorn"
    assert level1[1].lb and level1[1].lb_from == "Cancer" and level1[1].lb_to == "Capricorn"
    level2 = [period for period in timeline.levels[2] if period.start >= level1[0].start]
    assert level2, "expected second-level releasing periods"


def test_flag_peaks_by_fortune_modality() -> None:
    start = datetime(2000, 1, 1, tzinfo=UTC)
    end = datetime(2025, 1, 1, tzinfo=UTC)
    timeline = zr_periods("Aries", start, end, levels=1)
    flag_peaks_fortune(timeline, "Libra")
    peaks = [period for period in timeline.levels[1] if period.metadata.get("peak")]
    assert peaks, "expected peak annotations"
    for period in peaks:
        if period.sign == "Libra":
            assert period.metadata["peak"] == "major"
        else:
            assert period.metadata["peak"] == "moderate"
