from datetime import UTC, datetime, timedelta

from core.aspects_plus.scan import TimeWindow
from core.events_plus.detectors import detect_combust_cazimi, detect_voc_moon, next_sign_ingress


# Synthetic linear ephemeris
class LinearEphemeris:
    def __init__(self, t0, base, rates):
        self.t0, self.base, self.rates = t0, base, rates
    def __call__(self, ts):
        dt_days = (ts - self.t0).total_seconds() / 86400.0
        return {k: (self.base.get(k, 0.0) + self.rates.get(k, 0.0) * dt_days) % 360.0 for k in self.base}


def test_next_sign_ingress_moon():
    t0 = datetime(2025, 1, 1, tzinfo=UTC)
    eph = LinearEphemeris(t0, base={"Moon": 2.0}, rates={"Moon": 13.0})
    ingress = next_sign_ingress("Moon", t0, eph, step_minutes=60)  # Aries → Taurus crossing near 30°
    assert ingress is not None
    # Time to move from 2° to 30° at 13°/day ≈ (28/13) days
    expected = t0 + timedelta(days=28.0/13.0)
    assert abs((ingress - expected).total_seconds()) <= 60


def test_voc_moon_conjunction_only_segment_full_voc():
    # Moon moves through Aries; other bodies far → no conjunction before ingress
    t0 = datetime(2025, 1, 1, tzinfo=UTC)
    eph = LinearEphemeris(t0, base={"Moon": 2.0, "Sun": 180.0, "Venus": 200.0}, rates={"Moon": 13.0})
    win = TimeWindow(start=t0, end=t0 + timedelta(days=3))

    intervals = detect_voc_moon(
        window=win,
        provider=eph,
        aspects=["conjunction"],  # simplify for test
        policy={"per_object": {}, "per_aspect": {"conjunction": 8.0}, "adaptive_rules": {}},
        other_objects=["Sun", "Venus"],
        step_minutes=120,
    )
    # Expect a VoC interval for the Aries segment (start around t0, end at ingress)
    assert len(intervals) >= 1
    iv = intervals[0]
    assert iv.kind == "voc_moon"
    # end near ingress time computed above
    expected_end = t0 + timedelta(days=28.0/13.0)
    assert abs((iv.end - expected_end).total_seconds()) <= 90


def test_combust_cazimi_detection():
    # Mercury approaches the Sun and passes exact conjunction
    t0 = datetime(2025, 1, 1, tzinfo=UTC)
    eph = LinearEphemeris(t0, base={"Sun": 0.0, "Mercury": 0.5}, rates={"Sun": 0.0, "Mercury": -0.1})
    win = TimeWindow(start=t0, end=t0 + timedelta(days=20))

    intervals = detect_combust_cazimi(win, eph, planet="Mercury")
    # Should have at least a cazimi sub-interval
    kinds = {iv.kind for iv in intervals}
    assert "cazimi" in kinds
    # Ensure intervals are ordered and non-empty
    for iv in intervals:
        assert iv.end >= iv.start
