from datetime import UTC, datetime

import pytest

swe = pytest.importorskip(
    "swisseph",
    reason="pyswisseph not installed; install extras with `.[providers]`",
)

from astroengine.core.time import TimeConversion, ensure_utc, to_tt


def test_to_tt_returns_conversion():
    moment = datetime(2024, 3, 1, 12, 30, tzinfo=UTC)
    conversion = to_tt(moment)
    assert isinstance(conversion, TimeConversion)
    assert conversion.jd_tt > conversion.jd_utc
    assert conversion.delta_t_seconds > 50.0


def test_ensure_utc_converts_naive():
    naive = datetime(2024, 3, 1, 12, 30)
    assert ensure_utc(naive).tzinfo == UTC


def test_to_tt_matches_swisseph_delta():
    moment = datetime(2024, 5, 5, 6, 0, tzinfo=UTC)
    conversion = to_tt(moment)
    jd_tt, jd_ut = swe().utc_to_jd(
        moment.year,
        moment.month,
        moment.day,
        moment.hour,
        moment.minute,
        moment.second + moment.microsecond / 1e6,
        swe().GREG_CAL,
    )
    assert abs(conversion.jd_tt - jd_tt) < 1e-8
    assert abs(conversion.jd_utc - jd_ut) < 1e-8
    expected_delta = (jd_tt - jd_ut) * 86400.0
    assert abs(conversion.delta_t_seconds - expected_delta) < 1e-6
