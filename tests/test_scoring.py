# >>> AUTO-GEN BEGIN: AE Scoring Tests v1.0
from astroengine.scoring import (
    ScoreInputs,
    compute_score,
    compute_uncertainty_confidence,
)


def _s(orb_abs, orb_allow, phase="separating"):
    return compute_score(ScoreInputs(
        kind="antiscia", orb_abs_deg=orb_abs, orb_allow_deg=orb_allow,
        moving="mars", target="venus", applying_or_separating=phase,
    )).score


def _s_corridor(orb_abs, orb_allow, corridor):
    return compute_score(ScoreInputs(
        kind="antiscia",
        orb_abs_deg=orb_abs,
        orb_allow_deg=orb_allow,
        moving="mars",
        target="venus",
        applying_or_separating="separating",
        corridor_width_deg=corridor,
    )).score


def test_score_monotonic_decreases_with_orb():
    a = _s(0.1, 2.0)
    b = _s(1.0, 2.0)
    c = _s(1.9, 2.0)
    assert a > b > c


def test_applying_bias_raises_score():
    sep = _s(0.5, 2.0, phase="separating")
    app = _s(0.5, 2.0, phase="applying")
    assert app > sep


def test_partile_boost_triggers_near_exact():
    near = _s(0.05, 2.0)
    far = _s(0.30, 2.0)
    assert near > far


def test_corridor_width_modulates_score():
    tight = _s_corridor(0.5, 2.0, 1.0)
    wide = _s_corridor(0.5, 2.0, 3.0)
    assert tight > wide


def test_uncertainty_confidence_penalizes_observers():
    solo = compute_uncertainty_confidence(2.0, 2.0, observers=1)
    crowded = compute_uncertainty_confidence(2.0, 2.0, observers=10)
    assert solo > crowded
# >>> AUTO-GEN END: AE Scoring Tests v1.0
