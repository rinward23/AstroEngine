"""Unit tests for the synastry orchestrator."""

from __future__ import annotations

from astroengine.synastry.orchestrator import SynHit, compute_synastry


def test_compute_synastry_sorted_and_typed() -> None:
    a = {"ts": "1990-01-01T12:00:00Z", "lat": 40.7128, "lon": -74.0060}
    b = {"ts": "1985-06-15T08:30:00Z", "lat": 34.0522, "lon": -118.2437}

    hits = compute_synastry(a=a, b=b, aspects=(0, 60, 90, 120, 180), orb_deg=3.0)

    assert isinstance(hits, list)
    assert hits == sorted(
        hits, key=lambda h: (h.direction, h.moving, h.target, h.angle_deg, h.orb_abs)
    )
    for hit in hits:
        assert isinstance(hit, SynHit)
        assert hit.direction in {"A->B", "B->A"}


def test_compute_synastry_body_filters() -> None:
    a = {"ts": "2000-01-01T00:00:00Z", "lat": 51.5074, "lon": -0.1278}
    b = {"ts": "2001-07-01T00:00:00Z", "lat": 35.6895, "lon": 139.6917}

    hits = compute_synastry(
        a=a,
        b=b,
        aspects=(0, 60, 90, 120, 180),
        orb_deg=4.0,
        bodies_a=("Sun", "Moon"),
        bodies_b=("Mars", "Venus"),
    )
    for hit in hits:
        assert hit.moving in {"Sun", "Moon"}
        assert hit.target in {"Mars", "Venus"}
