# >>> AUTO-GEN BEGIN: AE Scoring Tests v1.0
from astroengine.scoring import compute_score, ScoreInputs


def _s(orb_abs, orb_allow, phase="separating"):
    return compute_score(ScoreInputs(
        kind="antiscia", orb_abs_deg=orb_abs, orb_allow_deg=orb_allow,
        moving="mars", target="venus", applying_or_separating=phase,
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
# >>> AUTO-GEN END: AE Scoring Tests v1.0
