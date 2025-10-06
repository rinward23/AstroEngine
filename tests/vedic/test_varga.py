from types import SimpleNamespace

import pytest

from astroengine.engine.vedic import (
    VARGA_DEFINITIONS,
    compute_varga,
    dasamsa_sign,
    navamsa_sign,
)


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

    assert result["Ascendant"]["start_sign"] == "Libra"
    assert result["Ascendant"]["segment_arc_degrees"] == pytest.approx(30.0 / 9.0)


def test_drekkana_triplicity_rule():
    positions = {"Sun": SimpleNamespace(longitude=15.0)}  # Aries 15°
    result = compute_varga(positions, "D3")
    sun = result["Sun"]
    assert sun["sign"] == "Leo"
    assert sun["drekkana"] == 2
    assert sun["start_sign"] == "Aries"
    assert sun["rule"] == VARGA_DEFINITIONS["D3"].rule_description


def test_saptamsa_even_sign_counts_from_seventh():
    positions = {"Moon": SimpleNamespace(longitude=35.0)}  # Taurus 5°
    result = compute_varga(positions, "D7")
    moon = result["Moon"]
    assert moon["sign"] == "Sagittarius"
    assert moon["start_sign"] == "Scorpio"
    assert moon["saptamsa"] == 2


def test_shashtiamsa_precision_even_sign():
    positions = {"Mars": SimpleNamespace(longitude=31.0)}  # Taurus 1°
    result = compute_varga(positions, "D60")
    mars = result["Mars"]
    assert mars["sign"] == "Sagittarius"
    assert mars["shashtiamsa"] == 3
    assert mars["segment_arc_degrees"] == pytest.approx(0.5)

