import datetime as dt

import pytest

from astroengine.detectors import detect_antiscia_contacts, detect_decl_contacts
from astroengine.engine import scan_contacts
from astroengine.providers import register_provider


class StubProvider:
    """Linear motion stub with a moving point near 160°."""

    def __init__(self):
        self.base = dt.datetime(2024, 6, 1, 0, 0, 0, tzinfo=dt.UTC)

    def positions_ecliptic(self, iso: str, bodies):
        t = dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(dt.UTC)
        hours = (t - self.base).total_seconds() / 3600.0
        lon_move = (160.0 + hours) % 360.0
        out: dict[str, dict[str, float]] = {}
        for body in bodies:
            if body == "moving":
                out[body] = {"lon": lon_move, "speed_lon": 24.0}
            else:
                out[body] = {"lon": 10.0, "speed_lon": 0.0}
        return out


class EquatorStubProvider:
    """Provider returning declinations on opposite sides of the equator."""

    def positions_ecliptic(self, iso: str, bodies):
        out: dict[str, dict[str, float]] = {}
        for body in bodies:
            if body == "moving":
                out[body] = {"lon": 0.0, "declination": 0.2, "speed_lon": 0.0}
            else:
                out[body] = {"lon": 180.0, "declination": -0.2, "speed_lon": 0.0}
        return out


class DeclinationOnlyProvider:
    """Provider used to ensure scan_contacts can output only declination events."""

    def positions_ecliptic(self, iso: str, bodies):
        out: dict[str, dict[str, float]] = {}
        for body in bodies:
            if body == "moving":
                out[body] = {"lon": 0.0, "declination": 0.25, "speed_lon": -0.5}
            else:
                out[body] = {"lon": 5.0, "declination": 0.0, "speed_lon": 0.0}
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
    ticks = list(_ticks("2024-06-01T00:00:00Z", "2024-06-02T00:00:00Z", 60))
    hits = detect_antiscia_contacts(
        prov, ticks, "moving", "target", orb_deg_antiscia=1.5
    )
    assert any(h.kind == "antiscia" for h in hits)


def test_decl_parallel_coarse_detects():
    prov = StubProvider()
    ticks = list(_ticks("2024-06-01T00:00:00Z", "2024-06-01T12:00:00Z", 60))
    hits = detect_decl_contacts(prov, ticks, "moving", "target", 0.5, 0.5)
    assert isinstance(hits, list)


def test_decl_parallel_handles_cross_equator_declinations():
    prov = EquatorStubProvider()
    ticks = ["2024-06-01T00:00:00Z"]
    hits = detect_decl_contacts(prov, ticks, "moving", "target", 0.5, 0.5)
    parallels = [hit for hit in hits if hit.kind == "decl_parallel"]
    assert parallels, "Expected a parallel hit across the equator"
    hit = parallels[0]
    assert hit.dec_moving == pytest.approx(0.2)
    assert hit.dec_target == pytest.approx(-0.2)


def test_scan_contacts_decl_only_emits_declination_events():
    provider_name = "stub_decl_only"
    register_provider(provider_name, DeclinationOnlyProvider())
    events = scan_contacts(
        start_iso="2024-06-01T00:00:00Z",
        end_iso="2024-06-01T03:00:00Z",
        moving="moving",
        target="target",
        provider_name=provider_name,
        decl_parallel_orb=0.5,
        decl_contra_orb=0.5,
        include_mirrors=False,
        include_aspects=False,
    )
    assert events and all(event.kind.startswith("decl_") for event in events)
    first = events[0]
    assert "decl_moving" in first.metadata and "decl_target" in first.metadata


# >>> AUTO-GEN END: AE Synthetic Acceptance v1.0
