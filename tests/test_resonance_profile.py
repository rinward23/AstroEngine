import pytest

from astroengine.profiles import (
    ResonanceWeights,
    load_base_profile,
    load_resonance_weights,
)


def test_resonance_weights_normalize_from_profile():
    profile = load_base_profile()
    weights = load_resonance_weights(profile)
    mapping = weights.as_mapping()
    assert pytest.approx(sum(mapping.values())) == 1.0
    assert all(value > 0.0 for value in mapping.values())


def test_custom_resonance_weights_normalize():
    weights = ResonanceWeights(2.0, 1.0, 1.0).normalized()
    assert pytest.approx(weights.mind + weights.body + weights.spirit) == 1.0
    assert weights.mind > weights.body

