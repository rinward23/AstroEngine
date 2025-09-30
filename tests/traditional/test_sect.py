from __future__ import annotations

from datetime import UTC, datetime

from astroengine.chart.natal import ChartLocation
from astroengine.engine.traditional.sect import sect_info


def test_day_and_night_sect_classification() -> None:
    location = ChartLocation(latitude=0.0, longitude=0.0)
    day_moment = datetime(2023, 7, 1, 12, 0, tzinfo=UTC)
    night_moment = datetime(2023, 7, 1, 0, 0, tzinfo=UTC)
    day_info = sect_info(day_moment, location)
    night_info = sect_info(night_moment, location)
    assert day_info.is_day is True
    assert day_info.luminary_of_sect == "Sun"
    assert night_info.is_day is False
    assert night_info.luminary_of_sect == "Moon"


def test_high_latitude_edge_case() -> None:
    location = ChartLocation(latitude=70.0, longitude=-50.0)
    moment = datetime(2023, 12, 21, 0, 0, tzinfo=UTC)
    info = sect_info(moment, location)
    assert info.sun_altitude_deg < 0.0
    assert info.is_day is False
