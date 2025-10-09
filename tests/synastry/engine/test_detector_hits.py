"""Unit tests for synastry engine hit detection."""

from __future__ import annotations

import pytest

from astroengine.synastry.engine import DEFAULT_ORB_POLICY, ChartPositions, detect_hits


def test_exact_angle_has_severity_one() -> None:
    pos_a = ChartPositions({"Sun": 10.0})
    pos_b = ChartPositions({"Moon": 130.0})
    hits = detect_hits(pos_a, pos_b, aspects=(120,), policy=DEFAULT_ORB_POLICY)
    assert len(hits) == 1
    hit = hits[0]
    assert hit.aspect == 120
    assert hit.delta == pytest.approx(0.0, abs=1e-9)
    assert hit.severity == pytest.approx(1.0, abs=1e-9)
    assert hit.orb == pytest.approx(DEFAULT_ORB_POLICY.effective_orb("Sun", "Moon", 120))


def test_outside_orb_excluded() -> None:
    pos_a = ChartPositions({"Sun": 10.0})
    pos_b = ChartPositions({"Moon": 137.0})  # 127° separation, 7° from trine
    hits = detect_hits(pos_a, pos_b, aspects=(120,), policy=DEFAULT_ORB_POLICY)
    assert hits == []


def test_node_axis_uses_nearest_anti_node() -> None:
    pos_a = ChartPositions({"True Node": 0.0})
    pos_b = ChartPositions({"Sun": 184.0})
    hits = detect_hits(pos_a, pos_b, aspects=(180,), policy=DEFAULT_ORB_POLICY)
    assert hits, "expected opposition to node axis"
    hit = hits[0]
    assert hit.aspect == 180
    assert hit.delta == pytest.approx(4.0, abs=1e-6)
    assert 0.0 < hit.severity < 1.0


def test_multiple_aspects_preserved() -> None:
    pos_a = ChartPositions({"Sun": 0.0})
    pos_b = ChartPositions({"Mars": 30.5})
    hits = detect_hits(pos_a, pos_b, aspects=(30, 45), policy=DEFAULT_ORB_POLICY)
    assert {hit.aspect for hit in hits} == {30}
    hit = hits[0]
    assert hit.delta == pytest.approx(0.5, abs=1e-6)
