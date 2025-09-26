from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import os

import pytest

from astroengine.detectors.directed_aspects import solar_arc_natal_aspects


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat().replace("+00:00", "Z")


def test_solar_arc_aspects_unit(monkeypatch: pytest.MonkeyPatch) -> None:
    import astroengine.detectors.directed_aspects as module

    class DummyPos:
        def __init__(self, longitude: float) -> None:
            self.longitude = longitude

    natal_positions = {
        "Sun": DummyPos(10.0),
        "Moon": DummyPos(58.0),
        "Mars": DummyPos(190.0),
    }

    def fake_compute_natal_chart(moment, location, *, bodies=None, **_kwargs):  # type: ignore[no-untyped-def]
        if bodies is not None:
            positions = {name: DummyPos(natal_positions[name].longitude) for name in bodies}
        else:
            positions = dict(natal_positions)
        return SimpleNamespace(positions=positions, location=location, moment=moment)

    start = datetime(2001, 6, 1, tzinfo=UTC)
    second = start + timedelta(days=1)
    sun_progression = {
        _iso(start): DummyPos(12.0),
        _iso(second): DummyPos(13.5),
    }

    def fake_progressed(natal_chart, target_moment, *, bodies=None, **_kwargs):  # type: ignore[no-untyped-def]
        iso = _iso(target_moment)
        return SimpleNamespace(chart=SimpleNamespace(positions={"Sun": sun_progression[iso]}))

    class DummyAdapter:
        @staticmethod
        def from_chart_config(_config):
            return SimpleNamespace()

    monkeypatch.setattr(module, "compute_natal_chart", fake_compute_natal_chart)
    monkeypatch.setattr(module, "compute_secondary_progressed_chart", fake_progressed)
    monkeypatch.setattr(module, "SwissEphemerisAdapter", DummyAdapter)

    hits = solar_arc_natal_aspects(
        natal_ts=_iso(start),
        start_ts=_iso(start),
        end_ts=_iso(second),
        aspects=(0, 60, 90, 120, 180),
        orb_deg=2.0,
        bodies=("Sun", "Moon", "Mars"),
        step_days=1.0,
    )

    assert isinstance(hits, list)
    assert hits == sorted(hits, key=lambda hit: (hit.when_iso, hit.moving, hit.target, hit.angle_deg))
    for hit in hits:
        assert hit.orb_abs <= hit.orb_allow + 1e-9


@pytest.mark.skipif(
    not any(os.environ.get(var) for var in ("SWE_EPH_PATH", "SE_EPHE_PATH")),
    reason="Swiss Ephemeris path not configured",
)
def test_solar_arc_aspects_integration() -> None:
    hits = solar_arc_natal_aspects(
        natal_ts="1990-01-01T12:00:00Z",
        start_ts="2020-01-01T00:00:00Z",
        end_ts="2020-01-03T00:00:00Z",
        aspects=(0, 60, 90, 120, 180),
        orb_deg=2.0,
        bodies=None,
        step_days=1.0,
    )

    assert isinstance(hits, list)
    assert hits == sorted(hits, key=lambda hit: (hit.when_iso, hit.moving, hit.target, hit.angle_deg))
    for hit in hits:
        assert hit.orb_abs <= hit.orb_allow + 1e-9
