from datetime import UTC, datetime, timedelta

from astroengine.core.transit_engine import TransitEngine


def test_mars_conjunct_natal_venus_acceptance():
    engine = TransitEngine.with_default_adapter()
    natal_venus_longitude = 240.9623186447056
    start = datetime(2025, 10, 20, tzinfo=UTC)
    end = datetime(2025, 11, 20, tzinfo=UTC)

    events = list(engine.scan_longitude_crossing(4, natal_venus_longitude, 0.0, start, end))
    assert events, "Expected at least one transit event"

    event = min(events, key=lambda evt: abs(evt.orb or 999.0))
    assert event.orb is not None and event.orb < 1.0 / 60.0
    assert event.motion in {"applying", "separating"}

    assert event.timestamp is not None
    window_center = datetime(2025, 11, 6, tzinfo=UTC)
    assert abs(event.timestamp - window_center) <= timedelta(hours=12)
