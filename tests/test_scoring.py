from __future__ import annotations

import pytest

from astroengine.scoring.contact import (
    ScoreInputs,
    compute_score,
    compute_uncertainty_confidence,
)
from astroengine.scoring.policy import load_severity_policy


def _score(
    kind: str, orb_abs: float, orb_allow: float, phase: str = "separating"
) -> float:
    return compute_score(
        ScoreInputs(
            kind=kind,
            orb_abs_deg=orb_abs,
            orb_allow_deg=orb_allow,
            moving="mars",
            target="venus",
            applying_or_separating=phase,
        )
    ).score


def test_score_monotonic_decreases_with_orb() -> None:
    a = _score("antiscia", 0.1, 2.0)
    b = _score("antiscia", 1.0, 2.0)
    c = _score("antiscia", 1.9, 2.0)
    assert a > b > c


def test_applying_bias_raises_score() -> None:
    sep = _score("antiscia", 0.5, 2.0, phase="separating")
    app = _score("antiscia", 0.5, 2.0, phase="applying")
    assert app > sep


def test_partile_boost_triggers_near_exact() -> None:
    near = _score("antiscia", 0.05, 2.0)
    far = _score("antiscia", 0.30, 2.0)
    assert near > far


def test_corridor_width_modulates_score() -> None:
    tight = compute_score(
        ScoreInputs(
            kind="antiscia",
            orb_abs_deg=0.5,
            orb_allow_deg=2.0,
            moving="mars",
            target="venus",
            applying_or_separating="separating",
            corridor_width_deg=1.0,
        )
    )
    wide = compute_score(
        ScoreInputs(
            kind="antiscia",
            orb_abs_deg=0.5,
            orb_allow_deg=2.0,
            moving="mars",
            target="venus",
            applying_or_separating="separating",
            corridor_width_deg=3.0,
        )
    )
    assert tight.components["confidence"] > wide.components["confidence"]


def test_uncertainty_confidence_penalizes_observers() -> None:
    solo = compute_uncertainty_confidence(2.0, 2.0, observers=1)
    crowded = compute_uncertainty_confidence(2.0, 2.0, observers=10)
    assert solo > crowded


def test_condition_and_dignity_modifiers_applied() -> None:
    inputs = ScoreInputs(
        kind="aspect_square",
        orb_abs_deg=0.2,
        orb_allow_deg=2.0,
        moving="mars",
        target="sun",
        applying_or_separating="applying",
        severity_modifiers={"retrograde": 0.9, "combust": 0.8, "out_of_bounds": 1.1},
        dignity_modifiers={"primary": "rulership", "support": "triplicity"},
        retrograde=True,
        combust_state="combust",
        out_of_bounds=True,
    )
    result = compute_score(inputs)
    assert result.components["condition_factor"] == pytest.approx(0.9 * 0.8 * 1.1)
    assert result.components["dignity_factor"] == pytest.approx(1.10 * 1.05)


def test_score_deterministic_for_same_inputs() -> None:
    inputs = ScoreInputs(
        kind="aspect_trine",
        orb_abs_deg=0.4,
        orb_allow_deg=2.0,
        moving="venus",
        target="saturn",
        applying_or_separating="separating",
        custom_modifiers={"angular_priority": 1.1},
    )
    first = compute_score(inputs)
    second = compute_score(inputs)
    assert first.score == pytest.approx(second.score)
    assert first.components == second.components


def test_orb_boundary_zeroes_score() -> None:
    inside = compute_score(
        ScoreInputs(
            kind="aspect_conjunction",
            orb_abs_deg=0.5,
            orb_allow_deg=1.0,
            moving="sun",
            target="moon",
            applying_or_separating="separating",
        )
    ).score
    at_edge = compute_score(
        ScoreInputs(
            kind="aspect_conjunction",
            orb_abs_deg=1.0,
            orb_allow_deg=1.0,
            moving="sun",
            target="moon",
            applying_or_separating="separating",
        )
    ).score
    beyond = compute_score(
        ScoreInputs(
            kind="aspect_conjunction",
            orb_abs_deg=1.2,
            orb_allow_deg=1.0,
            moving="sun",
            target="moon",
            applying_or_separating="separating",
        )
    ).score
    assert inside > 0.0
    assert at_edge == pytest.approx(0.0)
    assert beyond == pytest.approx(0.0)


def test_policy_override_changes_score() -> None:
    inputs = ScoreInputs(
        kind="aspect_conjunction",
        orb_abs_deg=0.2,
        orb_allow_deg=2.0,
        moving="sun",
        target="mars",
        applying_or_separating="separating",
    )
    baseline = compute_score(inputs)
    override_policy = load_severity_policy(
        overrides={"base_weights": {"aspect_conjunction": 1.10}}
    ).to_mapping()
    boosted = compute_score(inputs, policy=override_policy)
    assert boosted.score > baseline.score


def test_uncertainty_confidence_respects_precision() -> None:
    tight = compute_uncertainty_confidence(
        2.0,
        2.0,
        orb_abs_deg=0.1,
        resonance_weights={"mind": 1.0, "body": 1.0, "spirit": 1.0},
        uncertainty_bias={"narrow": "spirit", "broad": "body", "standard": "mind"},
    )
    loose = compute_uncertainty_confidence(
        2.0,
        2.0,
        orb_abs_deg=1.5,
        resonance_weights={"mind": 1.0, "body": 1.0, "spirit": 1.0},
        uncertainty_bias={"narrow": "spirit", "broad": "body", "standard": "mind"},
    )
    assert tight > loose


def test_tradition_profile_increases_drishti_focus() -> None:
    base = ScoreInputs(
        kind="aspect_square",
        orb_abs_deg=0.1,
        orb_allow_deg=6.0,
        moving="mars",
        target="saturn",
        applying_or_separating="applying",
        angle_deg=90.0,
        corridor_width_deg=2.0,
        resonance_weights={"mind": 1.0, "body": 1.0, "spirit": 1.0},
    )
    without_tradition = compute_score(base)
    with_tradition = compute_score(
        ScoreInputs(
            kind=base.kind,
            orb_abs_deg=base.orb_abs_deg,
            orb_allow_deg=base.orb_allow_deg,
            moving=base.moving,
            target=base.target,
            applying_or_separating=base.applying_or_separating,
            corridor_width_deg=base.corridor_width_deg,
            corridor_profile=base.corridor_profile,
            resonance_weights=base.resonance_weights,
            angle_deg=base.angle_deg,
            tradition_profile="vedic",
        )
    )
    assert with_tradition.score >= without_tradition.score
    assert with_tradition.components["tradition_factor"] >= 1.0


def test_fractal_factor_contributes_for_harmonic_angles() -> None:
    result = compute_score(
        ScoreInputs(
            kind="aspect_trine",
            orb_abs_deg=0.2,
            orb_allow_deg=4.0,
            moving="jupiter",
            target="sun",
            applying_or_separating="separating",
            angle_deg=120.0,
            corridor_width_deg=2.0,
            resonance_weights={"mind": 1.0, "body": 1.0, "spirit": 1.0},
        )
    )
    assert "fractal_factor" in result.components
    assert result.components["fractal_factor"] > 0.0
