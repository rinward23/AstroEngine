from datetime import UTC, datetime, timedelta

import pytest

from astroengine.ephemeris import EphemerisSample
from astroengine.core import transit_engine as te

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


class _DummyAdapter:
    def __init__(self, samples: dict[tuple[int, datetime], EphemerisSample]) -> None:
        self._samples = samples

    def sample(self, body: int, moment: datetime) -> EphemerisSample:  # pragma: no cover - exercised
        return self._samples[(body, moment)]


def _make_sample(longitude: float, speed: float) -> EphemerisSample:
    return EphemerisSample(
        jd_tt=0.0,
        jd_utc=0.0,
        longitude=longitude,
        latitude=0.0,
        distance=1.0,
        speed_longitude=speed,
        speed_latitude=0.0,
        speed_distance=0.0,
        delta_t_seconds=0.0,
    )


def test_transit_engine_compute_positions_uses_adapter() -> None:
    moment = datetime(2025, 1, 1, tzinfo=UTC)
    samples = {(1, moment): _make_sample(120.0, 0.1)}
    engine = TransitEngine(adapter=_DummyAdapter(samples))

    positions = engine.compute_positions([1], moment)
    assert positions == {1: pytest.approx(120.0)}


def test_scan_longitude_crossing_falls_back_on_refine_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    body = 1
    start = datetime(2025, 1, 1, tzinfo=UTC)
    end = start + timedelta(hours=6)

    samples = {
        (body, start): _make_sample(100.0, 0.5),
        (body, end): _make_sample(100.6, 0.5),
    }

    engine = TransitEngine(adapter=_DummyAdapter(samples))

    def _failing_refine(*_args, **_kwargs):
        raise RuntimeError("refine failure")

    monkeypatch.setattr(te, "refine_event", _failing_refine)

    events = list(engine.scan_longitude_crossing(body, 100.0, 0.0, start, end, step_hours=6.0))
    assert events, "Fallback path should still yield an event"
    event = events[0]
    assert event.timestamp == end
    assert event.motion in {"applying", "separating", "stationary"}

    canonical = list(
        te.to_canonical_events(
            [
                {
                    "timestamp": event.timestamp,
                    "moving": event.body,
                    "target": event.target,
                    "aspect": "conjunction",
                    "orb": event.orb,
                    "applying": event.motion == "applying",
                }
            ]
        )
    )
    assert canonical
