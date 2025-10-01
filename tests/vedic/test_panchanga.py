from datetime import UTC, datetime

from astroengine.engine.vedic import build_context, lunar_month


DELHI_LAT = 28.6139
DELHI_LON = 77.2090


def test_adhika_shravana_2023():
    moment = datetime(2023, 8, 1, 12, 0, tzinfo=UTC)
    context = build_context(moment, DELHI_LAT, DELHI_LON, ayanamsa="lahiri")
    month = lunar_month(context)

    assert month.name == "Shravana"
    assert month.adhika is True
    assert month.sun_sign == "Cancer"
    assert month.contains(moment)
    assert month.start.year == 2023 and month.end.year == 2023


def test_regular_ashwin_2023():
    moment = datetime(2023, 10, 15, 12, 0, tzinfo=UTC)
    context = build_context(moment, DELHI_LAT, DELHI_LON, ayanamsa="lahiri")
    month = lunar_month(context)

    assert month.name == "Ashwin"
    assert month.adhika is False
    assert month.sun_sign == "Virgo"
    assert month.contains(moment)
    assert month.start < moment < month.end
