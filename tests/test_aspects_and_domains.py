# >>> AUTO-GEN BEGIN: AE Aspects & Domains Tests v1.0
import datetime as dt

from astroengine.detectors_aspects import detect_aspects
from astroengine.domains import rollup_domain_scores


class StubProvider:
    def __init__(self):
        self.base = dt.datetime(2024, 6, 1, 0, 0, 0, tzinfo=dt.timezone.utc)

    def positions_ecliptic(self, iso: str, bodies):
        t = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        hours = (t - self.base).total_seconds() / 3600.0
        # moving marches 1°/hour from 0°; target fixed at 120° (trine target at 0°)
        out = {}
        for b in bodies:
            if b == "moving":
                out[b] = {"lon": (hours % 360.0), "speed_lon": 24.0}
            else:
                out[b] = {"lon": 120.0, "speed_lon": 0.0}
        return out


def _ticks(start, end, step_minutes=60):
    t0 = dt.datetime.fromisoformat(start.replace("Z", "+00:00"))
    t1 = dt.datetime.fromisoformat(end.replace("Z", "+00:00"))
    step = dt.timedelta(minutes=step_minutes)
    while t0 <= t1:
        yield t0.isoformat().replace("+00:00", "Z")
        t0 += step


def test_aspect_detector_finds_trine():
    prov = StubProvider()
    ticks = list(_ticks("2024-06-01T00:00:00Z", "2024-06-02T00:00:00Z", 60))
    hits = detect_aspects(prov, ticks, "moving", "target")
    kinds = {h.kind for h in hits}
    assert any(k.startswith("aspect_trine") for k in kinds)


def test_domain_rollup_has_three_domains():
    # Minimal glue: emulate engine.scan_contacts output with handcrafted events.
    events = [
        # Minimal event set to exercise rollup
        type(
            "E",
            (),
            {
                "kind": "aspect_trine",
                "when_iso": "2024-06-01T00:00:00Z",
                "moving": "venus",
                "target": "mars",
                "orb_abs": 0.5,
                "applying_or_separating": "applying",
                "score": 0.8,
            },
        )(),
        type(
            "E",
            (),
            {
                "kind": "aspect_square",
                "when_iso": "2024-06-01T01:00:00Z",
                "moving": "mars",
                "target": "saturn",
                "orb_abs": 0.5,
                "applying_or_separating": "separating",
                "score": 0.6,
            },
        )(),
    ]
    report = rollup_domain_scores(events)
    assert set(report.keys()) >= {"mind", "body", "spirit"}
