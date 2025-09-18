from astroengine.rulesets import get_vca_aspect, vca_orb_for


def test_major_angles_exist():
    assert get_vca_aspect("conjunction").angle == 0.0
    assert get_vca_aspect("opposition").angle == 180.0
    assert get_vca_aspect("square").angle == 90.0
    assert get_vca_aspect("trine").angle == 120.0
    assert get_vca_aspect("sextile").angle == 60.0


def test_minor_and_harmonics_present():
    assert get_vca_aspect("quincunx").angle == 150.0
    assert get_vca_aspect("quintile").angle == 72.0
    assert get_vca_aspect("septile").angle == 51.428
    assert get_vca_aspect("novile").angle == 40.0


def test_orb_policy_defaults():
    assert vca_orb_for("square") == 8.0
    assert vca_orb_for("quincunx") in (2.0, 3.0)
    assert vca_orb_for("vigintile") == 1.0
