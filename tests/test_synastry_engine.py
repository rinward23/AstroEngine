from core.relationship_plus.synastry import (
    overlay_positions,
    synastry_grid,
    synastry_hits,
    synastry_score,
)

POS_A = {"Sun": 350.0, "Moon": 20.0, "Mars": 100.0}
POS_B = {"Sun": 10.0, "Moon": 80.0, "Venus": 200.0}

POLICY = {
    "per_object": {},
    "per_aspect": {
        "conjunction": 8.0,
        "opposition": 7.0,
        "square": 6.0,
        "trine": 6.0,
        "sextile": 3.0,
        "quincunx": 3.0,
    },
    "adaptive_rules": {},
}
ASPECTS = ["conjunction", "opposition", "square", "trine", "sextile", "quincunx"]


def test_hits_detection_and_wrap():
    hits = synastry_hits(POS_A, POS_B, aspects=ASPECTS, policy=POLICY)
    assert any(h.a == "Sun" and h.b == "Sun" and h.aspect == "conjunction" for h in hits)
    assert any(h.a == "Moon" and h.b == "Moon" and h.aspect == "sextile" for h in hits)


def test_grid_and_overlay_shapes():
    hits = synastry_hits(POS_A, POS_B, aspects=ASPECTS, policy=POLICY)
    grid = synastry_grid(hits)
    assert "Sun" in grid and "Sun" in grid["Sun"]
    overlay = overlay_positions(POS_A, POS_B)
    assert overlay["Sun"]["ring"] in ("A", "B")


def test_scoring_aggregates_and_weights():
    hits = synastry_hits(
        POS_A,
        POS_B,
        aspects=ASPECTS,
        policy=POLICY,
        per_aspect_weight={"conjunction": 2.0},
    )
    summary = synastry_score(hits)
    assert summary["overall"] > 0
    assert summary["by_aspect"].get("conjunction", 0) >= summary["by_aspect"].get("sextile", 0)
