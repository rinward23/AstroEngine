from types import SimpleNamespace

import pytest

from astroengine.engine.vedic import compute_varga, dasamsa_sign, navamsa_sign


def test_navamsa_movable_sign():
    sign_idx, longitude, pada = navamsa_sign(5.0)
    assert sign_idx == 1  # Taurus
    assert longitude == pytest.approx(45.0, abs=1e-6)
    assert pada == 2


def test_dasamsa_dual_sign():
    sign_idx, longitude, part = dasamsa_sign(275.0)  # Capricorn 5°
    assert sign_idx == 10  # Aquarius
    assert part == 2
    assert 300.0 < longitude < 330.0


def test_compute_varga_includes_ascendant():
    positions = {
        "Sun": SimpleNamespace(longitude=15.0),
        "Moon": SimpleNamespace(longitude=123.0),
    }
    result = compute_varga(positions, "D9", ascendant=83.0)
    assert "Ascendant" in result
    assert "pada" in result["Ascendant"]
