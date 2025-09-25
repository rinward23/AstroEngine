"""Packaging smoke tests ensuring astroengine is importable."""

# >>> AUTO-GEN BEGIN: astroengine packaging smoke v1.0
import importlib

import pytest


@pytest.mark.smoke
def test_import_astroengine_surface():
    module = importlib.import_module("astroengine")
    assert hasattr(module, "TransitEngine")
    assert hasattr(module, "TransitScanConfig")
    assert hasattr(module, "TransitEvent")


# >>> AUTO-GEN END: astroengine packaging smoke v1.0
