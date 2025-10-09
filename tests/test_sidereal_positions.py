from __future__ import annotations

from datetime import UTC, datetime

import pytest

swe = pytest.importorskip(
    "swisseph",
    reason="pyswisseph not installed; install extras with `.[providers]`",
)

from astroengine.chart.config import ChartConfig
from astroengine.engine.ephe_runtime import init_ephe
from astroengine.ephemeris import SwissEphemerisAdapter


def _expected_sidereal_longitude(jd_ut: float, mode: int) -> float:
    swe_module = swe()
    base_flag = init_ephe()
    swe_module.set_sid_mode(mode, 0, 0)
    values, _ = swe_module.calc_ut(
        jd_ut, swe_module.SUN, base_flag | swe_module.FLG_SIDEREAL
    )
    return float(values[0]) % 360.0


def test_sun_lahiri_sidereal_zero() -> None:
    moment = datetime(2000, 4, 13, 11, 52, 10, 808741, tzinfo=UTC)
    adapter = SwissEphemerisAdapter(
        chart_config=ChartConfig(zodiac="sidereal", ayanamsha="lahiri")
    )
    if adapter.ephemeris_path:
        init_ephe(adapter.ephemeris_path, force=True)
    jd_ut = adapter.julian_day(moment)
    position = adapter.body_position(jd_ut, swe().SUN, body_name="Sun")
    expected = _expected_sidereal_longitude(jd_ut, swe().SIDM_LAHIRI)
    assert abs(position.longitude - expected) < 1e-6


def test_sun_fagan_bradley_sidereal_zero() -> None:
    moment = datetime(1950, 4, 14, 13, 50, 30, 293000, tzinfo=UTC)
    adapter = SwissEphemerisAdapter(
        chart_config=ChartConfig(zodiac="sidereal", ayanamsha="fagan_bradley")
    )
    if adapter.ephemeris_path:
        init_ephe(adapter.ephemeris_path, force=True)
    jd_ut = adapter.julian_day(moment)
    position = adapter.body_position(jd_ut, swe().SUN, body_name="Sun")
    expected = _expected_sidereal_longitude(jd_ut, swe().SIDM_FAGAN_BRADLEY)
    assert abs(position.longitude - expected) < 1e-6
