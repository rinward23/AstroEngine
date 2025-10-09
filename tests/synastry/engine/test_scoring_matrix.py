"""Scoring aggregation tests for synastry engine."""

from __future__ import annotations

import pytest

from astroengine.synastry.engine import DEFAULT_WEIGHTS, Hit, Weights, compute_scores


def test_scores_grouped_by_family() -> None:
    hits = [
        Hit(bodyA="Sun", bodyB="Moon", aspect=120, delta=0.0, orb=6.0, severity=1.0),
        Hit(bodyA="Mars", bodyB="Saturn", aspect=90, delta=1.0, orb=6.0, severity=0.5),
    ]
    scores = compute_scores(hits, DEFAULT_WEIGHTS)
    assert scores.raw_total == pytest.approx(1.5)
    assert scores.overall == pytest.approx(1.44 + 0.4)
    assert scores.by_aspect_family["harmonious"] == pytest.approx(1.44)
    assert scores.by_aspect_family["challenging"] == pytest.approx(0.4)
    assert scores.by_body_family["luminary"] == pytest.approx(2.88)
    assert scores.by_body_family["personal"] == pytest.approx(0.4)
    assert scores.by_body_family["social"] == pytest.approx(0.4)


def test_custom_weights_affect_scores() -> None:
    weights = Weights(
        aspect_family={"harmonious": 2.0, "challenging": 0.5, "neutral": 1.0},
        body_family={"luminary": 1.0, "personal": 1.0, "social": 1.0, "outer": 1.0, "points": 1.0},
        conjunction_sign=0.5,
    )
    hit = Hit(bodyA="Sun", bodyB="Moon", aspect=0, delta=0.5, orb=8.0, severity=0.8)
    score = compute_scores([hit], weights)
    expected = 0.8 * 1.0 * 1.0 * 1.0 * 0.5  # severity * aspect * bodyA * bodyB * conj
    assert score.overall == pytest.approx(expected)
    assert score.by_aspect_family["neutral"] == pytest.approx(expected)
    assert score.by_body_family["luminary"] == pytest.approx(expected * 2)
