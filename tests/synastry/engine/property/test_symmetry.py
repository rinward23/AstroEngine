"""Symmetry tests ensuring swapped charts mirror hits."""

from __future__ import annotations

from astroengine.synastry.engine import (
    ChartPositions,
    DEFAULT_ASPECT_SET,
    DEFAULT_ORB_POLICY,
    detect_hits,
)


def test_synastry_symmetry() -> None:
    pos_a = ChartPositions({"Sun": 10.0, "Moon": 200.0, "True Node": 15.0})
    pos_b = ChartPositions({"Sun": 190.0, "Moon": 20.0, "True Node": 195.0})
    hits_ab = detect_hits(pos_a, pos_b, aspects=DEFAULT_ASPECT_SET, policy=DEFAULT_ORB_POLICY)
    hits_ba = detect_hits(pos_b, pos_a, aspects=DEFAULT_ASPECT_SET, policy=DEFAULT_ORB_POLICY)
    forward = {(hit.body_a, hit.body_b, hit.aspect, round(hit.delta, 6)) for hit in hits_ab}
    reverse = {(hit.body_b, hit.body_a, hit.aspect, round(hit.delta, 6)) for hit in hits_ba}
    assert forward == reverse

