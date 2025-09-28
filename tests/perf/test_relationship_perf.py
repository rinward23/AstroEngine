from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.rel_plus.synastry import clear_synastry_memoization, synastry_interaspects

BASELINE_PATH = Path(__file__).with_name("baseline_synastry.json")


@pytest.mark.benchmark(group="relationship")
def test_synastry_benchmark(benchmark):
    baseline = json.loads(BASELINE_PATH.read_text())
    pos_a = {f"A{i}": (i * 17) % 360 for i in range(1, 14)}
    pos_b = {f"B{i}": (i * 23 + 45) % 360 for i in range(1, 14)}
    aspects = [
        "conjunction",
        "opposition",
        "square",
        "trine",
        "sextile",
        "quincunx",
        "semisquare",
        "sesquisquare",
        "quintile",
        "biquintile",
        "semi-sextile",
        "semi-square",
        "sesquiquadrate",
    ]
    policy = {
        "per_aspect": {asp: 6.0 for asp in aspects},
        "adaptive_rules": {},
    }

    def run_synastry():
        clear_synastry_memoization()
        return synastry_interaspects(pos_a, pos_b, aspects, policy)

    result = benchmark(run_synastry)
    stats = benchmark.stats
    mean = stats["mean"]
    median = stats["median"]
    assert mean <= baseline["mean"] * 1.1
    assert median <= baseline["median"] * 1.1
    assert len(result) > 0
