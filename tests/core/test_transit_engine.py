"""Regression coverage for :mod:`astroengine.core.transit_engine`."""

from __future__ import annotations

import datetime as _dt

import pytest

import astroengine.core as core
from astroengine.core.transit_engine import _aspect_definitions
from astroengine.ephemeris.adapter import EphemerisSample


class FakeEphemerisAdapter:
    """Minimal ephemeris adapter that records sampling operations."""

    def __init__(self) -> None:
        self.calls: list[tuple[int, _dt.datetime]] = []

    def sample(self, body: int, moment: _dt.datetime) -> EphemerisSample:
        self.calls.append((body, moment))
        base = float(body) * 10.0
        return EphemerisSample(
            jd_tt=0.0,
            jd_utc=0.0,
            longitude=base,
            latitude=0.0,
            distance=1.0,
            speed_longitude=0.1,
            speed_latitude=0.0,
            speed_distance=0.0,
            right_ascension=0.0,
            declination=0.0,
            speed_right_ascension=0.0,
            speed_declination=0.0,
            delta_t_seconds=0.0,
        )

    def signature(self) -> tuple[str]:
        return ("fake",)

    @property
    def call_count(self) -> int:
        return len(self.calls)


def test_default_aspect_catalogue_includes_minor_and_harmonic_entries():
    """Ensure callers get the full default catalogue without configuration."""

    defaults = _aspect_definitions(None)
    catalogue = {name: (angle, family) for name, angle, family in defaults}

    assert "semiquintile" in catalogue, "minor aspects should be enabled by default"
    assert catalogue["semiquintile"][1] == "minor"
    assert catalogue["semiquintile"][0] == pytest.approx(36.0)

    assert "septile" in catalogue, "harmonic aspects should be enabled by default"
    assert catalogue["septile"][1] == "harmonic"
    assert catalogue["septile"][0] == pytest.approx(51.4286)


def test_resolve_settings_fast_mode_disables_refinement():
    config = core.TransitEngineConfig(
        refinement_mode="accurate",
        fast_min_step_seconds=0.5,
    )

    fast_settings = config.resolve_settings("fast")

    assert fast_settings.enabled is False
    assert fast_settings.max_iterations == 0
    assert fast_settings.min_step_seconds == pytest.approx(1.0)


def test_resolve_settings_accurate_mode_enforces_positive_iterations():
    config = core.TransitEngineConfig(
        accurate_iterations=0,
        accurate_min_step_seconds=15.0,
    )

    accurate_settings = config.resolve_settings("accurate")

    assert accurate_settings.enabled is True
    assert accurate_settings.max_iterations == 1
    assert accurate_settings.min_step_seconds == pytest.approx(15.0)


def test_resolve_settings_rejects_unknown_mode():
    config = core.TransitEngineConfig()

    with pytest.raises(ValueError):
        config.resolve_settings("experimental")


def test_compute_positions_respects_cache_toggle():
    moment = _dt.datetime(2024, 1, 1, tzinfo=_dt.UTC)
    bodies = [1, 1]

    cached_engine = core.TransitEngine(
        adapter=FakeEphemerisAdapter(),
        config=core.TransitEngineConfig(cache_samples=True),
    )
    cached_engine.compute_positions(bodies, moment)
    assert cached_engine.adapter.call_count == 1

    uncached_engine = core.TransitEngine(
        adapter=FakeEphemerisAdapter(),
        config=core.TransitEngineConfig(cache_samples=False),
    )
    uncached_engine.compute_positions(bodies, moment)
    assert uncached_engine.adapter.call_count == 2


def test_scan_longitude_crossing_validates_time_window():
    engine = core.TransitEngine(adapter=FakeEphemerisAdapter())
    start = _dt.datetime(2024, 1, 2, tzinfo=_dt.UTC)
    end = _dt.datetime(2024, 1, 1, tzinfo=_dt.UTC)

    with pytest.raises(ValueError, match="start <= end"):
        list(
            engine.scan_longitude_crossing(
                body=1,
                reference_longitude=0.0,
                aspect_angle_deg=0.0,
                start=start,
                end=end,
            )
        )


def test_scan_longitude_crossing_rejects_non_positive_steps():
    engine = core.TransitEngine(adapter=FakeEphemerisAdapter())
    start = _dt.datetime(2024, 1, 1, tzinfo=_dt.UTC)
    end = _dt.datetime(2024, 1, 3, tzinfo=_dt.UTC)

    with pytest.raises(ValueError, match="step_hours must be positive"):
        list(
            engine.scan_longitude_crossing(
                body=1,
                reference_longitude=0.0,
                aspect_angle_deg=0.0,
                start=start,
                end=end,
                step_hours=0.0,
            )
        )
