from astroengine.scoring.orb import DEFAULT_ASPECTS, OrbCalculator


def test_defaults_present():
    required = (0, 60, 90, 120, 180, 30, 45, 72, 150)
    for angle in required:
        assert any(abs(a - angle) < 1e-3 for a in DEFAULT_ASPECTS)


def test_orb_major_vs_minor():
    calc = OrbCalculator()
    assert calc.orb_for('Sun', 'Mars', 180) >= 4.0
    assert calc.orb_for('Sun', 'Mars', 150) <= 2.0
