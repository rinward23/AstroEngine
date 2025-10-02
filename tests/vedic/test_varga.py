from types import SimpleNamespace

import pytest

from astroengine.engine.vedic import (
    compute_varga,
    dasamsa_sign,
    navamsa_sign,
    rasi_sign,
    saptamsa_sign,
    trimsamsa_sign,
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


def test_trimsamsa_segments_for_odd_sign():
    sign_idx, longitude, payload = trimsamsa_sign(2.0)  # Aries 2°
    assert sign_idx == 0  # Aries
    assert payload == {"segment": 1, "ruler": "Mars"}
    assert longitude == pytest.approx(12.0, abs=1e-6)


def test_trimsamsa_segments_for_even_sign():
    sign_idx, longitude, payload = trimsamsa_sign(35.0)  # Taurus 5°
    assert sign_idx == 1  # Taurus
    assert payload == {"segment": 1, "ruler": "Venus"}
    assert longitude == pytest.approx(60.0, abs=1e-6)


def test_compute_varga_supports_extended_set():
    positions = {"Sun": SimpleNamespace(longitude=1.0)}
    d1 = compute_varga(positions, "D1")
    d7 = compute_varga(positions, "D7")
    d30 = compute_varga(positions, "D30")
    assert d1["Sun"]["sign"] == "Aries"
    assert "segment" in d7["Sun"]
    assert d7["Sun"]["segment"] == 1
    assert d30["Sun"]["ruler"] == "Mars"


def test_rasi_sign_matches_natal_longitude():
    sign_idx, longitude, extra = rasi_sign(213.5)
    assert sign_idx == 7  # Scorpio
    assert longitude == pytest.approx(213.5 % 360.0)
    assert extra == {}


def test_saptamsa_even_sign_start():
    sign_idx, longitude, payload = saptamsa_sign(95.0)  # Cancer (even sign)
    assert payload["segment"] == 2
    assert sign_idx == 10  # Aquarius
    assert longitude == pytest.approx(305.0, abs=1e-6)

