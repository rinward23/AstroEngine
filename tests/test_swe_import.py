# >>> AUTO-GEN BEGIN: Test Swiss Ephemeris Import v1.0

import swisseph as swe


def test_pyswisseph_imports():
    assert hasattr(swe, "SUN") and hasattr(swe, "calc_ut")

# >>> AUTO-GEN END: Test Swiss Ephemeris Import v1.0
