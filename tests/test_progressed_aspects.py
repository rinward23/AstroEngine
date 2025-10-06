from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from astroengine.detectors.progressed_aspects import progressed_natal_aspects


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat().replace("+00:00", "Z")


def test_progressed_aspects_unit(monkeypatch: pytest.MonkeyPatch) -> None:
    import astroengine.detectors.progressed_aspects as module

    class DummyPos:
        def __init__(self, longitude: float, speed: float = 0.0) -> None:
            self.longitude = longitude
            self.speed_longitude = speed

    natal_positions = {
        "Sun": DummyPos(10.0),
        "Moon": DummyPos(70.0),
        "Mars": DummyPos(200.0),
    }

    def fake_compute_natal_chart(moment, location, *, bodies=None, **_kwargs):  # type: ignore[no-untyped-def]
        if bodies is not None:
            positions = {name: DummyPos(natal_positions[name].longitude) for name in bodies}
        else:
            positions = dict(natal_positions)
        return SimpleNamespace(positions=positions, location=location, moment=moment)

    start = datetime(2000, 1, 1, tzinfo=UTC)
    second = start + timedelta(days=1)
    timeline = {
        _iso(start): {
            "Sun": DummyPos(10.0, 0.9),
            "Moon": DummyPos(69.0, 13.0),
            "Mars": DummyPos(190.0, 0.6),
        },
        _iso(second): {
            "Sun": DummyPos(10.9, 0.9),
            "Moon": DummyPos(71.2, 13.0),
            "Mars": DummyPos(189.0, -0.5),
        },
    }

    def fake_progressed(natal_chart, target_moment, *, bodies=None, **_kwargs):  # type: ignore[no-untyped-def]
        iso = _iso(target_moment)
        positions = timeline[iso]
        if bodies is not None:
            positions = {name: positions[name] for name in bodies}
        return SimpleNamespace(chart=SimpleNamespace(positions=positions))

    class DummyAdapter:
        @staticmethod
        def from_chart_config(_config):
            return SimpleNamespace()

    monkeypatch.setattr(module, "compute_natal_chart", fake_compute_natal_chart)
    monkeypatch.setattr(module, "compute_secondary_progressed_chart", fake_progressed)
    monkeypatch.setattr(module, "SwissEphemerisAdapter", DummyAdapter)

    hits = progressed_natal_aspects(
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
        assert hit.speed_deg_per_day is not None


@pytest.mark.skipif(
    not any(os.environ.get(var) for var in ("SWE_EPH_PATH", "SE_EPHE_PATH")),
    reason="Swiss Ephemeris path not configured",
)
def test_progressed_aspects_integration() -> None:
    hits = progressed_natal_aspects(
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
