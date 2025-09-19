from datetime import UTC, datetime

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
