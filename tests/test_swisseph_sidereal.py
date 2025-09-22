from datetime import UTC, datetime

import swisseph as swe

from astroengine.chart.config import ChartConfig
from astroengine.ephemeris import SwissEphemerisAdapter


def test_sidereal_adapter_sets_lahiri_mode() -> None:
    jd = swe.julday(2024, 3, 20, 0.0)
    swe.set_sid_mode(swe.SIDM_FAGAN_BRADLEY)
    expected = None
    try:
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        expected = swe.get_ayanamsa(jd)
    finally:
        swe.set_sid_mode(swe.SIDM_FAGAN_BRADLEY)

    adapter = SwissEphemerisAdapter(
        chart_config=ChartConfig(zodiac="sidereal", ayanamsha="lahiri")
    )
    adapter.julian_day(datetime(2024, 3, 20, tzinfo=UTC))

    actual = swe.get_ayanamsa(jd)
    try:
        assert expected is not None
        assert abs(actual - expected) < 1e-6
    finally:
        swe.set_sid_mode(swe.SIDM_FAGAN_BRADLEY)


def test_house_system_mapping_uses_config() -> None:
    adapter = SwissEphemerisAdapter(
        chart_config=ChartConfig(zodiac="tropical", ayanamsha=None, house_system="whole_sign")
    )
    jd = adapter.julian_day(datetime(2024, 3, 20, tzinfo=UTC))
    houses = adapter.houses(jd, latitude=0.0, longitude=0.0)
    assert houses.system == "W"
