from datetime import datetime, timedelta, timezone

from astroengine.engine.lots import aspects_to_lots, scan_lot_events
from astroengine.engine.lots.aspects import AspectHit
from astroengine.engine.lots.events import LotEvent
from astroengine.scoring.policy import OrbPolicy


def _policy(default: float = 5.0) -> OrbPolicy:
    return OrbPolicy({"defaults": {"default": default}})


def test_aspects_detection():
    lots = {"Fortune": 100.0}
    bodies = {"Mars": 100.5}
    hits = aspects_to_lots(lots, bodies, _policy(), [1])
    assert hits, "expected conjunction"
    hit = hits[0]
    assert isinstance(hit, AspectHit)
    assert hit.angle == 0.0
    assert hit.orb == 0.5
    assert hit.severity > 0


class LinearEphemeris:
    def __init__(self, start: datetime, base: float, speed: float) -> None:
        self.start = start
        self.base = base
        self.speed = speed

    class Sample:
        def __init__(self, longitude: float, speed_longitude: float) -> None:
            self.longitude = longitude
            self.speed_longitude = speed_longitude

    def sample(self, body: str, moment: datetime):
        delta_days = (moment - self.start).total_seconds() / 86400.0
        longitude = (self.base + self.speed * delta_days) % 360.0
        return self.Sample(longitude, self.speed)


def test_event_scan_linear_motion():
    start = datetime(2023, 1, 1, tzinfo=timezone.utc)
    ephem = LinearEphemeris(start, base=0.0, speed=1.0)
    lot_lambda = 10.0
    events = scan_lot_events(
        ephem,
        lot_lambda,
        ["Mars"],
        start,
        start + timedelta(days=20),
        _policy(),
        [1],
        step_hours=12.0,
        lot_name="Fortune",
    )
    assert events, "expected conjunction event"
    event = events[0]
    assert isinstance(event, LotEvent)
    assert abs(event.angle - 0.0) < 1e-6
    assert event.timestamp >= start + timedelta(days=9)
    assert event.timestamp <= start + timedelta(days=11)


def test_event_scan_checks_each_angle():
    start = datetime(2023, 1, 1, tzinfo=timezone.utc)
    ephem = LinearEphemeris(start, base=0.0, speed=30.0)
    events = scan_lot_events(
        ephem,
        0.0,
        ["Mars"],
        start,
        start + timedelta(days=7),
        _policy(),
        [1, 4],
        step_hours=6.0,
        lot_name="Fortune",
    )
    angles = {round(event.angle, 6) for event in events}
    assert {0.0, 90.0}.issubset(angles)
