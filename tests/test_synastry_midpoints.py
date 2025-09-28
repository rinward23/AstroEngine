"""Unit tests for synastry midpoint scanning."""

from __future__ import annotations

import math

import pytest

from astroengine.core.rel_plus.composite import ChartPositions, EclipticPos
from astroengine.synastry.midpoints import scan_midpoints


def _chart(positions: dict[str, float]) -> ChartPositions:
    return {name: EclipticPos(lon=lon, lat=0.0) for name, lon in positions.items()}


def test_midpoint_hit_detection_and_scoring() -> None:
    positions_a = _chart({"Sun": 10.0, "Mercury": 16.0, "Mars": 200.0})
    positions_b = _chart({"Venus": 20.0, "Moon": 140.0})

    result = scan_midpoints(positions_a, positions_b, top_k=2)
    payload = result.to_dict()

    hits = payload["midpoint_hits"]
    assert any(hit["probeBody"] == "Mercury" for hit in hits)

    mercury_hit = next(
        hit
        for hit in hits
        if hit["srcA"] == "Sun" and hit["srcB"] == "Venus" and hit["probeBody"] == "Mercury"
    )
    assert pytest.approx(mercury_hit["mid_lon"], abs=1e-9) == 15.0
    assert pytest.approx(mercury_hit["offset"], abs=1e-9) == 1.0
    assert pytest.approx(mercury_hit["orb"], abs=1e-9) == 1.5
    assert pytest.approx(mercury_hit["severity"], abs=1e-9) == 0.25
    # Score = severity * weight_probe (1.0) * weight_sun (1.2) * weight_venus (1.0)
    assert pytest.approx(mercury_hit["score"], abs=1e-9) == 0.3

    hotspots = payload["hotspots"]
    assert hotspots, "Hotspots should be populated"
    top_entry = next(
        item for item in hotspots if item["srcA"] == "Sun" and item["srcB"] == "Venus"
    )
    assert top_entry["summary_score_a"] >= 0.0
    assert top_entry["summary_score_b"] >= 0.0
    assert top_entry["top_probes"], "Expected at least one top probe"


def test_node_axis_uses_shorter_offset() -> None:
    positions_a = _chart({"Mars": 200.0})
    positions_b = _chart({"Venus": 240.0, "Mean_Node": 40.0})

    result = scan_midpoints(positions_a, positions_b)
    payload = result.to_dict()

    node_hit = next(
        hit
        for hit in payload["midpoint_hits"]
        if hit["srcA"] == "Mars" and hit["srcB"] == "Venus" and hit["probeBody"].lower().endswith("node")
    )
    assert math.isclose(node_hit["offset"], 0.0, abs_tol=1e-9)
    assert math.isclose(node_hit["severity"], 1.0, abs_tol=1e-9)
    assert node_hit["score"] > 0.0

