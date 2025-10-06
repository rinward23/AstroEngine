"""Tests for composite, Davison, and synastry helpers."""

import math
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta

import pytest

from astroengine.core.rel_plus.composite import (
    BirthEvent,
    Body,
    ChartPositions,
    DavisonResult,
    EclipticPos,
    circular_midpoint,
    composite_midpoint_positions,
    composite_midpoints,
    davison_chart,
    davison_positions,
    geodesic_midpoint,
    midpoint_time,
)
from astroengine.core.rel_plus.synastry import synastry_grid, synastry_interaspects


class LinearEphemeris:
    """Simple linear ephemeris for deterministic testing."""

    def __init__(self, t0, base, rates):
        self.t0 = t0
        self.base = base
        self.rates = rates

    def __call__(self, ts):
        dt_days = (ts - self.t0).total_seconds() / 86400.0
        return {
            key: (self.base.get(key, 0.0) + self.rates.get(key, 0.0) * dt_days) % 360.0
            for key in self.base
        }


POLICY = {
    "per_object": {},
    "per_aspect": {
        "sextile": 3.0,
        "trine": 6.0,
        "square": 6.0,
        "conjunction": 8.0,
    },
    "adaptive_rules": {},
}


def test_circular_midpoint_wrap():
    assert abs(circular_midpoint(350.0, 10.0) - 0.0) < 1e-9
    assert abs(circular_midpoint(10.0, 350.0) - 0.0) < 1e-9


def test_composite_midpoint_positions():
    pos_a = {"Sun": 10.0, "Moon": 200.0}
    pos_b = {"Sun": 50.0, "Moon": 220.0}
    out = composite_midpoint_positions(pos_a, pos_b, ["Sun", "Moon"])
    assert abs(out["Sun"] - 30.0) < 1e-9
    assert abs(out["Moon"] - 210.0) < 1e-9


def test_composite_midpoint_positions_missing_body():
    pos_a = {"Sun": 10.0}
    pos_b = {"Sun": 50.0}
    with pytest.raises(KeyError):
        composite_midpoint_positions(pos_a, pos_b, ["Sun", "Mars"])


def test_composite_midpoints_handles_wrap_and_latitude():
    chart_a = {
        Body("Sun"): EclipticPos(lon=350.0, lat=5.0),
        Body("Moon"): EclipticPos(lon=120.0, lat=-2.5),
    }
    chart_b = {
        Body("Sun"): EclipticPos(lon=10.0, lat=-1.0),
        Body("Moon"): EclipticPos(lon=240.0, lat=4.5),
    }
    result = composite_midpoints(chart_a, chart_b, [Body("Sun"), Body("Moon")])
    assert math.isclose(result[Body("Sun")].lon, 0.0, abs_tol=1e-9)
    assert math.isclose(result[Body("Sun")].lat, 2.0, abs_tol=1e-9)
    assert math.isclose(result[Body("Moon")].lon, 180.0, abs_tol=1e-9)
    assert math.isclose(result[Body("Moon")].lat, 1.0, abs_tol=1e-9)


def test_davison_positions_time_midpoint():
    t0 = datetime(2025, 1, 1, tzinfo=UTC)
    t1 = t0 + timedelta(days=10)
    eph = LinearEphemeris(
        t0,
        base={"Sun": 0.0, "Venus": 20.0},
        rates={"Sun": 1.0, "Venus": 1.2},
    )
    pos = davison_positions(
        ["Sun", "Venus"],
        t0,
        t1,
        eph,
        lat_a=40.0,
        lon_a=-75.0,
        lat_b=-35.0,
        lon_b=150.0,
    )
    assert abs(pos["Sun"] - 5.0) < 1e-9
    assert abs(pos["Venus"] - (20.0 + 6.0)) < 1e-9


def test_midpoint_time_and_geodesic_midpoint():
    dt_a = datetime(2024, 6, 1, 12, tzinfo=UTC)
    dt_b = datetime(2024, 6, 3, 12, tzinfo=UTC)
    mid = midpoint_time(dt_a, dt_b)
    assert mid == datetime(2024, 6, 2, 12, tzinfo=UTC)

    lat, lon = geodesic_midpoint(0.0, 0.0, 0.0, 180.0)
    assert math.isclose(lat, 0.0, abs_tol=1e-9)
    assert math.isclose(abs(lon), 90.0, abs_tol=1e-4)


class StubEphemeris:
    def __init__(self) -> None:
        self.calls: list[tuple[datetime, float, float, tuple[str, ...]]] = []

    def positions_at(
        self,
        when: datetime,
        lat: float,
        lon: float,
        bodies: Iterable[Body],
        node_policy,
    ) -> ChartPositions:
        self.calls.append((when, lat, lon, tuple(str(b) for b in bodies)))
        return {
            Body("Sun"): EclipticPos(lon=100.0, lat=0.0, dist=1.0, speed_lon=1.0, retrograde=False),
            Body("Venus"): EclipticPos(lon=220.0, lat=1.0, dist=0.7, speed_lon=-1.2, retrograde=True),
        }


def test_davison_chart_records_midpoint_location():
    event_a = BirthEvent(datetime(2024, 1, 1, tzinfo=UTC), lat=40.0, lon=-75.0)
    event_b = BirthEvent(datetime(2024, 1, 11, tzinfo=UTC), lat=-35.0, lon=150.0)
    eph = StubEphemeris()
    result: DavisonResult = davison_chart(event_a, event_b, [Body("Sun"), Body("Venus")], eph)

    assert result.mid_when == midpoint_time(event_a.when, event_b.when)
    expected_lat, expected_lon = geodesic_midpoint(event_a.lat, event_a.lon, event_b.lat, event_b.lon)
    assert math.isclose(result.mid_lat, expected_lat, abs_tol=1e-9)
    assert math.isclose(result.mid_lon, expected_lon, abs_tol=1e-9)
    assert Body("Sun") in result.positions
    assert Body("Venus") in result.positions
    assert eph.calls, "Ephemeris should be invoked"


def test_synastry_interaspects_and_grid():
    pos_a = {"Mars": 10.0, "Sun": 0.0}
    pos_b = {"Venus": 70.0, "Moon": 180.0}

    hits = synastry_interaspects(
        pos_a,
        pos_b,
        ["sextile", "trine", "square", "conjunction"],
        POLICY,
    )
    assert any(
        hit["a_obj"] == "Mars"
        and hit["b_obj"] == "Venus"
        and hit["aspect"] == "sextile"
        for hit in hits
    )

    grid = synastry_grid(hits)
    assert grid["Mars"]["Venus"] == 1
