"""Regression coverage for :mod:`astroengine.core.transit_engine`."""

import pytest

from astroengine.core.transit_engine import _aspect_definitions


def test_default_aspect_catalogue_includes_minor_and_harmonic_entries():
    """Ensure callers get the full default catalogue without configuration."""

    defaults = _aspect_definitions(None)
    catalogue = {name: (angle, family) for name, angle, family in defaults}

    assert "semiquintile" in catalogue, "minor aspects should be enabled by default"
    assert catalogue["semiquintile"][1] == "minor"
    assert catalogue["semiquintile"][0] == pytest.approx(36.0)

    assert "septile" in catalogue, "harmonic aspects should be enabled by default"
    assert catalogue["septile"][1] == "harmonic"
    assert catalogue["septile"][0] == pytest.approx(51.4286)
