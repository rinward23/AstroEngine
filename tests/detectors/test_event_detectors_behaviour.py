"""Behavioural tests for lunations, eclipses, and aspect detectors."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

import astroengine.detectors.directed_aspects as directed
import astroengine.detectors.eclipses as eclipses
import astroengine.detectors.lunations as lunations
import astroengine.detectors.progressed_aspects as progressed


def test_find_lunations_classifies_phases_and_skips_failed_roots(
    detector_stubs, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lunations, "sun_lon", lambda jd: 0.0)
    monkeypatch.setattr(lunations, "moon_lon", lambda jd: (jd * 180.0) % 360.0)

    call_count = 0

    def sometimes_failing_solver(fn, left, right, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ValueError("boom")
        return detector_stubs.solve(fn, left, right, **kwargs)

    monkeypatch.setattr(lunations, "solve_zero_crossing", sometimes_failing_solver)

    start_jd = detector_stubs.origin
    events = lunations.find_lunations(start_jd, start_jd + 4.0, step_hours=12.0)
    phases = [event.phase for event in events]

    assert "new_moon" in phases
    assert "full_moon" in phases  # the second solve succeeds

    assert lunations.find_lunations(start_jd + 2.0, start_jd + 1.0) == []


def test_solar_arc_aspects_honor_orb_and_skip_invalid_ranges(
    detector_stubs, monkeypatch: pytest.MonkeyPatch
) -> None:
    start = datetime(1970, 1, 1, tzinfo=UTC)

    natal_positions = {
        "Sun": SimpleNamespace(longitude=0.0),
        "Mars": SimpleNamespace(longitude=0.0),
    }
    natal_chart = SimpleNamespace(positions=natal_positions)

    def fake_progressed_chart(*_args, **_kwargs):
        moment = _kwargs["current"] if "current" in _kwargs else _args[1]
        delta_days = int((moment - start).total_seconds() // 86400)
        longitude = 90.0 if delta_days == 0 else 120.0
        positions = {"Sun": SimpleNamespace(longitude=longitude, speed_longitude=1.0)}
        return SimpleNamespace(chart=SimpleNamespace(positions=positions))

    monkeypatch.setattr(directed, "compute_natal_chart", lambda *args, **kwargs: natal_chart)
    monkeypatch.setattr(directed, "compute_secondary_progressed_chart", fake_progressed_chart)

    hits = directed.solar_arc_natal_aspects(
        "1970-01-01T00:00:00Z",
        "1970-01-01T00:00:00Z",
        "1970-01-02T00:00:00Z",
        aspects=[90],
        orb_deg=1.0,
        bodies=["Sun", "Mars"],
        step_days=1.0,
    )

    pairs = {(hit.moving, hit.target) for hit in hits}
    assert pairs == {("Sun", "Mars"), ("Mars", "Sun")}
    assert all(hit.kind == "solar_arc_natal_aspect" for hit in hits)
    assert all(hit.angle_deg == pytest.approx(90.0) for hit in hits)
    mars_hit = next(hit for hit in hits if hit.moving == "Mars" and hit.target == "Sun")
    assert mars_hit.applying_or_separating == "exact"
    assert not mars_hit.retrograde

    assert (
        directed.solar_arc_natal_aspects(
            "1970-01-01T00:00:00Z",
            "1970-01-02T00:00:00Z",
            "1970-01-01T00:00:00Z",
            aspects=[90],
            orb_deg=1.0,
        )
        == []
    )


def test_progressed_aspects_track_motion_and_orb(detector_stubs, monkeypatch: pytest.MonkeyPatch) -> None:
    start = datetime(1970, 1, 1, tzinfo=UTC)

    natal_positions = {
        "Sun": SimpleNamespace(longitude=0.0),
        "Mars": SimpleNamespace(longitude=0.0),
    }
    natal_chart = SimpleNamespace(positions=natal_positions)

    def fake_progressed_chart(*_args, **_kwargs):
        moment = _kwargs["current"] if "current" in _kwargs else _args[1]
        delta_days = int((moment - start).total_seconds() // 86400)
        longitude = {0: 90.0, 1: 92.0}.get(delta_days, 95.0)
        positions = {
            "Sun": SimpleNamespace(longitude=0.0, speed_longitude=0.0),
            "Mars": SimpleNamespace(longitude=longitude, speed_longitude=0.5),
        }
        return SimpleNamespace(chart=SimpleNamespace(positions=positions))

    monkeypatch.setattr(progressed, "compute_natal_chart", lambda *args, **kwargs: natal_chart)
    monkeypatch.setattr(progressed, "compute_secondary_progressed_chart", fake_progressed_chart)

    hits = progressed.progressed_natal_aspects(
        "1970-01-01T00:00:00Z",
        "1970-01-01T00:00:00Z",
        "1970-01-03T00:00:00Z",
        aspects=[90],
        orb_deg=2.0,
        bodies=["Sun", "Mars"],
        step_days=1.0,
    )

    mars_hits = [
        hit for hit in hits if hit.moving == "Mars" and hit.target == "Sun"
    ]
    assert [hit.applying_or_separating for hit in mars_hits[:2]] == ["exact", "separating"]
    assert all(hit.family == "progressed-natal" for hit in hits)

    assert (
        progressed.progressed_natal_aspects(
            "1970-01-01T00:00:00Z",
            "1970-01-02T00:00:00Z",
            "1970-01-01T00:00:00Z",
            aspects=[90],
            orb_deg=1.0,
        )
        == []
    )


def test_find_eclipses_classifies_events_and_normalizes_location(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_swe = SimpleNamespace(
        SUN=0,
        MOON=1,
        FLG_SPEED=1,
        ECL_VISIBLE=1,
    )

    start = 2451545.0

    def sol_glob(jd, _flags):
        return (1, [start + 1.0, 0.0, 0.0, 0.0]) if (jd - start) < 1.5 else (0, [])

    def lun_glob(jd, _flags):
        return (1, [start + 2.0, 0.0, 0.0, 0.0]) if (jd - start) < 2.5 else (0, [])

    def sol_loc(_start, _geopos, _flags):
        raise RuntimeError("no visibility")

    def lun_loc(_start, _geopos, _flags):
        return (0, [], [])

    fake_swe.sol_eclipse_when_glob = sol_glob
    fake_swe.lun_eclipse_when = lun_glob
    fake_swe.sol_eclipse_when_loc = sol_loc
    fake_swe.lun_eclipse_when_loc = lun_loc

    monkeypatch.setattr(eclipses, "has_swe", lambda: True)
    monkeypatch.setattr(eclipses, "swe", lambda: fake_swe)
    monkeypatch.setattr(eclipses, "init_ephe", lambda: 0)
    monkeypatch.setattr(
        eclipses, "calc_ut_cached", lambda jd, *_: ([0.0, jd - start], 1)
    )
    monkeypatch.setattr(eclipses, "sun_lon", lambda jd: (jd - start) * 30.0)
    monkeypatch.setattr(
        eclipses,
        "moon_lon",
        lambda jd: (jd - start) * 30.0 + (180.0 if jd - start >= 2.0 else 0.0),
    )

    events = eclipses.find_eclipses(start, start + 3.0, location=(0.0, 0.0))
    assert [event.eclipse_type for event in events] == ["solar", "lunar"]
    assert events[0].is_visible is None
    assert events[1].is_visible is False
    assert events[0].moon_latitude == pytest.approx(1.0)

    assert eclipses.find_eclipses(start + 2.0, start + 1.0) == []
    with pytest.raises(ValueError):
        eclipses.find_eclipses(start, start + 1.0, location=(0.0,))
