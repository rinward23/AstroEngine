from __future__ import annotations

from datetime import UTC, datetime

import pytest

pytest.importorskip(
    "swisseph",
    reason="pyswisseph not installed; install extras with `pip install -e .[ephem,providers]`.",
)

from astroengine.chart.config import ChartConfig
from astroengine.chart.natal import ChartLocation, compute_natal_chart
from astroengine.engine.horary.hour_ruler import GeoLocation, planetary_hour
from astroengine.engine.horary.profiles import get_profile
from astroengine.engine.horary.rulers import house_ruler, sign_from_longitude
from astroengine.engine.horary.significators import choose_significators


def test_significators_match_house_rulers() -> None:
    location = GeoLocation(latitude=40.7128, longitude=-74.0060)
    moment = datetime(2024, 5, 10, 14, 30, tzinfo=UTC)
    chart = compute_natal_chart(
        moment=moment,
        location=ChartLocation(latitude=location.latitude, longitude=location.longitude),
        config=ChartConfig(house_system="placidus"),
    )

    hour = planetary_hour(moment, location)
    profile = get_profile("Lilly")
    sigset = choose_significators(
        chart,
        quesited_house=10,
        profile=profile,
        is_day_chart=hour.sunrise <= moment <= hour.sunset,
    )

    asc_sign = sign_from_longitude(chart.houses.ascendant)
    assert sigset.querent.body == house_ruler(asc_sign)

    mc_sign = sign_from_longitude(chart.houses.cusps[9])
    assert sigset.quesited.body == house_ruler(mc_sign)

    assert sigset.moon.body == "Moon"
    assert isinstance(sigset.querent.dignities.score, float)
    assert isinstance(sigset.quesited.dignities.score, float)

