# >>> AUTO-GEN BEGIN: Test Swiss Ephemeris Import v1.0

import pytest

swe = pytest.importorskip(
    "swisseph",
    reason="pyswisseph not installed; install extras with `.[providers]`",
)


def test_pyswisseph_imports():
    assert hasattr(swe, "SUN") and hasattr(swe, "calc_ut")


# >>> AUTO-GEN END: Test Swiss Ephemeris Import v1.0
