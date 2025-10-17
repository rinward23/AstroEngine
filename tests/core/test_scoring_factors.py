"""Unit tests for :func:`astroengine.core.scoring.compute_domain_factor`."""

from __future__ import annotations

import math

import pytest

from astroengine.core.scoring import compute_domain_factor


def test_weighted_method_averages_domain_probabilities():
    domains = {"career": 2.0, "love": 1.0}
    multipliers = {"career": 1.5, "love": 0.5}

    factor = compute_domain_factor(domains, multipliers, method="weighted")

    expected = (2 / 3) * 1.5 + (1 / 3) * 0.5
    assert factor == pytest.approx(expected)


def test_weighted_method_handles_negative_multipliers():
    domains = {"career": 3.0, "love": 1.0}
    multipliers = {"career": -0.5, "love": 0.25}

    factor = compute_domain_factor(domains, multipliers, method="weighted")

    expected = (3 / 4) * -0.5 + (1 / 4) * 0.25
    assert factor == pytest.approx(expected)


def test_method_returns_unity_when_total_weight_is_zero():
    domains = {"career": 0.0, "love": -2.0}

    factor = compute_domain_factor(domains, {"career": 10.0}, method="weighted")

    assert factor == pytest.approx(1.0)


def test_top_method_picks_highest_probability_domain():
    domains = {"career": 5.0, "love": 1.0}
    multipliers = {"career": 1.2, "love": 9.9}

    factor = compute_domain_factor(domains, multipliers, method="top")

    assert factor == pytest.approx(1.2)


def test_softmax_method_produces_temperature_weighted_average():
    domains = {"career": 2.0, "love": 1.0}
    multipliers = {"career": 2.0, "love": 1.0}

    factor = compute_domain_factor(domains, multipliers, method="softmax", temperature=1.0)

    expected_distribution = {
        "career": 1.0 / (1.0 + math.exp(-math.log(2))),
        "love": math.exp(-math.log(2)) / (1.0 + math.exp(-math.log(2))),
    }
    expected = sum(expected_distribution[key] * multipliers[key] for key in multipliers)
    assert factor == pytest.approx(expected)


def test_softmax_method_clamps_negative_multipliers():
    domains = {"career": 1.0, "love": 1.0}
    multipliers = {"career": -2.0, "love": -1.0}

    factor = compute_domain_factor(domains, multipliers, method="softmax", temperature=0.5)

    assert factor == pytest.approx((-2.0 + -1.0) / 2)
