from __future__ import annotations

from datetime import datetime, timezone

import pytest

from astroengine.chart.natal import ChartLocation
from astroengine.ux.maps.transit_overlay import (
    OverlayBodyState,
    OverlayOptions,
    OverlayRequest,
    compute_overlay_frames,
    compute_transit_aspects,
    render_overlay_svg,
    scale_au,
)


def _state(body: str, lon: float) -> OverlayBodyState:
    return OverlayBodyState(
        id=body,
        lon_deg=lon,
        lat_deg=0.0,
        radius_au=1.0,
        speed_lon_deg_per_day=0.0,
        speed_lat_deg_per_day=0.0,
        speed_radius_au_per_day=0.0,
        retrograde=False,
        frame="geocentric",
        metadata=None,
    )


def test_scale_au_piecewise() -> None:
    inner = scale_au(0.5)
    middle = scale_au(2.0)
    outer = scale_au(10.0)
    assert inner < middle < outer
    assert scale_au(0.0) == 0.0


def test_compute_transit_aspects_detection() -> None:
    natal = {"sun": _state("sun", 10.0)}
    transit = {"sun": _state("sun", 10.4)}
    hits = compute_transit_aspects(natal, transit)
    assert hits and hits[0].kind == "conjunction"

    transit["sun"] = _state("sun", 190.0)
    hits = compute_transit_aspects(natal, transit)
    assert any(hit.kind == "opposition" for hit in hits)


def test_compute_overlay_frames_smoke() -> None:
    pytest.importorskip("swisseph")
    request = OverlayRequest(
        birth_dt=datetime(1990, 1, 1, 12, tzinfo=timezone.utc),
        birth_location=ChartLocation(latitude=40.7128, longitude=-74.0060),
        transit_dt=datetime(2024, 3, 20, 12, tzinfo=timezone.utc),
        bodies=[
            "sun",
            "moon",
            "mercury",
            "venus",
            "mars",
            "jupiter",
            "saturn",
            "uranus",
            "neptune",
            "pluto",
            "mean_node",
            "asc",
            "mc",
        ],
        options=OverlayOptions(),
    )
    result = compute_overlay_frames(request)
    assert "sun" in result.natal.heliocentric
    assert "sun" in result.transit.geocentric
    aspects = compute_transit_aspects(result.natal.geocentric, result.transit.geocentric)
    svg = render_overlay_svg(result, aspects=aspects, width=600, height=600)
    assert svg.startswith("<svg")
