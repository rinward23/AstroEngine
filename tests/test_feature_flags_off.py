# >>> AUTO-GEN BEGIN: tests-feature-flags v1.0
from __future__ import annotations
import importlib


def test_experimental_detectors_default_off():
    eng = importlib.import_module("astroengine.engine")
    assert getattr(eng, "FEATURE_LUNATIONS", False) is False
    assert getattr(eng, "FEATURE_ECLIPSES", False) is False
    assert getattr(eng, "FEATURE_STATIONS", False) is False
    assert getattr(eng, "FEATURE_PROGRESSIONS", False) is False
    assert getattr(eng, "FEATURE_DIRECTIONS", False) is False
    assert getattr(eng, "FEATURE_RETURNS", False) is False
    assert getattr(eng, "FEATURE_PROFECTIONS", False) is False
    assert getattr(eng, "FEATURE_TIMELORDS", False) is False
# >>> AUTO-GEN END: tests-feature-flags v1.0
