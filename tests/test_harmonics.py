"""Unit tests for harmonic angle utilities."""

import json
from pathlib import Path

from astroengine.core.aspects_plus.harmonics import (
    BASE_ASPECTS,
    base_aspect_angles,
    combined_angles,
    harmonic_angles,
)

EPS = 1e-6


def approx(a: float, b: float, eps: float = EPS) -> bool:
    return abs(a - b) <= eps


def test_base_aspect_angles_classic():
    values = base_aspect_angles(["sextile", "square", "trine", "bogus"])
    assert values == [60.0, 90.0, 120.0]


def test_base_aspects_cover_policy_catalogue():
    policy_path = Path("profiles/aspects_policy.json")
    policy = json.loads(policy_path.read_text())
    for name, angle in policy.get("angles_deg", {}).items():
        key = name.strip().lower()
        assert key in BASE_ASPECTS
        assert abs(float(BASE_ASPECTS[key]) - float(angle)) <= 1e-4


def test_harmonic_5_and_7():
    h5 = harmonic_angles(5)
    assert len(h5) == 2 and approx(h5[0], 72.0) and approx(h5[1], 144.0)

    h7 = harmonic_angles(7)
    assert len(h7) == 3
    assert 51.428 - EPS <= h7[0] <= 51.429 + EPS
    assert 102.857 - EPS <= h7[1] <= 102.858 + EPS
    assert 154.285 - EPS <= h7[2] <= 154.286 + EPS


def test_combined_angles_dedup_and_sort():
    values = combined_angles(["square", "biquintile"], [5])
    assert values == [72.0, 90.0, 144.0]
