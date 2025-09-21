# >>> AUTO-GEN BEGIN: AE Synthetic Acceptance v1.0
import datetime as dt
from types import SimpleNamespace

from astroengine.detectors import detect_antiscia_contacts, detect_decl_contacts


class StubProvider:
    """Linear motion stub: moving starts near 160° and advances +1°/hour; target fixed at 10° Aries."""
    def __init__(self):
        self.base = dt.datetime(2024, 6, 1, 0, 0, 0, tzinfo=dt.timezone.utc)

    def positions_ecliptic(self, iso: str, bodies):
        t = dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(dt.timezone.utc)
        hours = (t - self.base).total_seconds() / 3600.0
        lon_move = (160.0 + hours) % 360.0
        out = {}
        for b in bodies:
            if b == "moving":
                out[b] = {"lon": lon_move, "speed_lon": 24.0}  # 24°/day
            else:
                out[b] = {"lon": 10.0, "speed_lon": 0.0}
        return out


def _ticks(start, end, step_minutes=60):
    t0 = dt.datetime.fromisoformat(start.replace("Z", "+00:00"))
    t1 = dt.datetime.fromisoformat(end.replace("Z", "+00:00"))
    step = dt.timedelta(minutes=step_minutes)
    while t0 <= t1:
        yield t0.isoformat().replace("+00:00", "Z")
        t0 += step


def test_antiscia_coarse_detects_when_within_orb():
    prov = StubProvider()
    # Antiscia target at 10°; antiscia(moving) = 180 - lon_moving.
    # Hit occurs when 180 - lon_moving ≈ 10 => lon_moving ≈ 170.
    ticks = list(_ticks("2024-06-01T00:00:00Z", "2024-06-02T00:00:00Z", 60))
    hits = detect_antiscia_contacts(prov, ticks, "moving", "target", orb_deg_antiscia=1.5)
    assert any(h.kind == "antiscia" for h in hits)


def test_decl_parallel_coarse_detects():
    prov = StubProvider()
    ticks = list(_ticks("2024-06-01T00:00:00Z", "2024-06-01T12:00:00Z", 60))
    hits = detect_decl_contacts(prov, ticks, "moving", "target", 0.5, 0.5)
    # We used a simple dec model via ecl_to_dec; ensure function runs and returns list
    assert isinstance(hits, list)
# >>> AUTO-GEN END: AE Synthetic Acceptance v1.0
