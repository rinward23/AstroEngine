from __future__ import annotations

import math

import pytest

from astroengine.esoteric import (
    chakra_correspondences,
    chakra_emphasis,
    chakra_emphasis_for_chart,
)
from astroengine.vca import DomainW


def test_chakra_dataset_contains_all_centers() -> None:
    dataset = chakra_correspondences()
    assert len(dataset) == 7
    for chakra in dataset:
        weights = chakra.normalized_domains()
        assert math.isclose(sum(weights.values()), 1.0, rel_tol=1e-6)
        assert set(weights.keys()) == {"MIND", "BODY", "SPIRIT"}


def test_chakra_emphasis_normalizes_distribution() -> None:
    dataset = chakra_correspondences()
    domain_map = {
        "mars": DomainW(0.1, 0.8, 0.3),
        "mercury": DomainW(0.6, 0.2, 0.2),
        "sun": DomainW(0.3, 0.3, 0.4),
        "venus": DomainW(0.2, 0.3, 0.5),
        "jupiter": DomainW(0.4, 0.2, 0.4),
        "saturn": DomainW(0.5, 0.1, 0.4),
        "moon": DomainW(0.2, 0.5, 0.3),
    }
    emphasis = chakra_emphasis(domain_map, dataset=dataset)
    assert math.isclose(sum(emphasis.values()), 1.0, rel_tol=1e-6)
    assert set(emphasis.keys()) == {chakra.id for chakra in dataset}
    # Muladhara should outrank Svadhisthana when Mars carries the strongest body weight.
    assert emphasis["muladhara"] > emphasis["svadhisthana"]


def test_chakra_emphasis_uniform_fallback() -> None:
    dataset = chakra_correspondences()
    emphasis = chakra_emphasis({}, dataset=dataset)
    expected = pytest.approx(1.0 / len(dataset))
    for value in emphasis.values():
        assert value == expected


def test_chakra_emphasis_for_chart_uses_vca_weights(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[object, str, str]] = []

    def _fake_weights(chart: object, body: str, system: str, profile=None):  # type: ignore[override]
        calls.append((chart, body, system))
        return DomainW(1.0, 1.0, 1.0)

    monkeypatch.setattr("astroengine.esoteric.chakras.weights_for_body", _fake_weights)
    emphasis = chakra_emphasis_for_chart(object())
    assert math.isclose(sum(emphasis.values()), 1.0, rel_tol=1e-6)
    assert calls  # at least one body was evaluated via the VCA house helper
