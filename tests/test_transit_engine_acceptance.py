import random
from datetime import UTC, datetime, timedelta


from astroengine.core.transit_engine import TransitEngine, TransitEngineConfig



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



def test_transit_engine_refinement_modes():
    start = datetime(2025, 10, 20, tzinfo=UTC)
    end = datetime(2025, 11, 20, tzinfo=UTC)
    natal_venus_longitude = 240.9623186447056

    engine_fast = TransitEngine.with_default_adapter(
        engine_config=TransitEngineConfig(
            coarse_step_hours=24.0,
            refinement_mode="fast",
        )
    )
    engine_accurate = TransitEngine.with_default_adapter(
        engine_config=TransitEngineConfig(
            coarse_step_hours=24.0,
            refinement_mode="accurate",
        )
    )

    fast_events = list(
        engine_fast.scan_longitude_crossing(4, natal_venus_longitude, 0.0, start, end)
    )
    accurate_events = list(
        engine_accurate.scan_longitude_crossing(4, natal_venus_longitude, 0.0, start, end)
    )

    assert fast_events and accurate_events

    def best(events):
        return min(events, key=lambda evt: abs(evt.orb or 999.0))

    fast_event = best(fast_events)
    accurate_event = best(accurate_events)

    assert fast_event.orb is not None and accurate_event.orb is not None
    assert fast_event.orb >= accurate_event.orb
    assert fast_event.timestamp is not None and accurate_event.timestamp is not None
    if fast_event.orb > accurate_event.orb:
        assert fast_event.timestamp != accurate_event.timestamp
    assert fast_event.timestamp.hour == start.hour
    assert fast_event.timestamp.minute == start.minute


def test_scan_longitude_crossing_fuzz_no_crash():
    engine = TransitEngine.with_default_adapter(
        engine_config=TransitEngineConfig(
            coarse_step_hours=12.0,
            refinement_mode="fast",
        )
    )
    rng = random.Random(0xA57A)
    base = datetime(2024, 1, 1, tzinfo=UTC)
    aspect_choices = [0.0, 30.0, 45.0, 60.0, 90.0, 120.0, 150.0, 180.0]
    body_codes = list(range(0, 10))

    for _ in range(24):
        start_offset = rng.uniform(-365, 365)
        duration_days = rng.uniform(1, 120)
        start = base + timedelta(days=start_offset)
        end = start + timedelta(days=duration_days)
        reference_longitude = rng.uniform(0.0, 360.0)
        aspect_angle = rng.choice(aspect_choices)
        body = rng.choice(body_codes)
        refinement = "accurate" if rng.random() < 0.5 else "fast"
        step = 6.0 if rng.random() < 0.5 else 12.0

        events = list(
            engine.scan_longitude_crossing(
                body,
                reference_longitude,
                aspect_angle,
                start,
                end,
                step_hours=step,
                refinement=refinement,
            )
        )
        for event in events:
            assert event.timestamp is not None
            assert event.orb is not None

