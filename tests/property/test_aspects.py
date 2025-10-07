from __future__ import annotations

import os
from typing import Any

import pytest

from astroengine.detectors.directed_aspects import solar_arc_natal_aspects
from astroengine.detectors.progressed_aspects import progressed_natal_aspects

hypothesis = pytest.importorskip("hypothesis")
given = hypothesis.given
settings = hypothesis.settings
st = hypothesis.strategies

SE_OK = bool(os.environ.get("SE_EPHE_PATH") or os.environ.get("SWE_EPH_PATH"))
ANGLES = (0.0, 60.0, 90.0, 120.0, 180.0)
ORB_STRATEGY = st.floats(
    min_value=0.5,
    max_value=3.0,
    allow_nan=False,
    allow_infinity=False,
)


def _orb_abs(hit: Any) -> float:
    return float(hit.orb_abs)


def _angle_value(hit: Any) -> float:
    if hasattr(hit, "angle_deg"):
        return float(hit.angle_deg)
    return float(hit.angle)


def _sorted_hits(hits: list[Any]) -> list[Any]:
    return sorted(hits, key=lambda h: (h.when_iso, h.moving, h.target, _angle_value(h)))


def _assert_hits_within_orb(hits: list[Any], orb: float) -> None:
    for hit in hits:
        assert _orb_abs(hit) <= orb + 1e-6
        angle = _angle_value(hit)
        assert any(abs(angle - candidate) <= 1e-6 for candidate in ANGLES)


@settings(deadline=None)
@given(orb=ORB_STRATEGY)
def test_progressed_aspects_respect_orb(orb: float) -> None:
    if not SE_OK:
        pytest.skip("Swiss ephemeris path not configured")

    try:
        hits = progressed_natal_aspects(
            natal_ts="1990-01-01T12:00:00Z",
            start_ts="2020-01-01T00:00:00Z",
            end_ts="2020-01-05T00:00:00Z",
            aspects=tuple(int(a) for a in ANGLES),
            orb_deg=float(orb),
        )
    except NotImplementedError:
        pytest.skip("progressed natal aspects detector not implemented")

    assert hits == _sorted_hits(hits)
    _assert_hits_within_orb(list(hits), float(orb))


@settings(deadline=None)
@given(orb=ORB_STRATEGY)
def test_solar_arc_aspects_respect_orb(orb: float) -> None:
    if not SE_OK:
        pytest.skip("Swiss ephemeris path not configured")

    try:
        hits = solar_arc_natal_aspects(
            natal_ts="1990-01-01T12:00:00Z",
            start_ts="2020-01-01T00:00:00Z",
            end_ts="2020-01-05T00:00:00Z",
            aspects=tuple(int(a) for a in ANGLES),
            orb_deg=float(orb),
        )
    except NotImplementedError:
        pytest.skip("solar arc aspects detector not implemented")

    assert hits == _sorted_hits(hits)
    _assert_hits_within_orb(list(hits), float(orb))
