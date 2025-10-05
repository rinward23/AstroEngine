from __future__ import annotations

import math
from pathlib import Path

import pytest

from astroengine.analysis.midpoints import (
    compute_midpoints,
    get_midpoint_settings,
    midpoint_longitude,
)
from astroengine.config import load_settings, save_settings


def test_midpoint_longitude_wraparound() -> None:
    assert math.isclose(midpoint_longitude(10.0, 350.0), 0.0, abs_tol=1e-9)


def test_compute_midpoints_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASTROENGINE_HOME", str(tmp_path))
    settings = load_settings()
    settings.midpoints.enabled = True
    settings.midpoints.tree.enabled = True
    settings.midpoints.tree.max_depth = 2
    settings.midpoints.include_nodes = True
    save_settings(settings)
    get_midpoint_settings(force_reload=True)

    data = {"Sun": 0.0, "Moon": 120.0, "Mercury": 240.0}
    result = compute_midpoints(data)

    def pair_matches(pair: tuple[str, str], names: set[str]) -> bool:
        return set(pair) == names

    assert any(pair_matches(pair, {"Sun", "Moon"}) for pair in result)

    def depth(pair: tuple[str, str]) -> int:
        return max(segment.count("/") for segment in pair) + 1

    assert any(depth(pair) > 1 for pair in result)


def test_compute_midpoints_excludes_nodes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASTROENGINE_HOME", str(tmp_path))
    settings = load_settings()
    settings.midpoints.enabled = True
    settings.midpoints.include_nodes = True
    settings.midpoints.tree.enabled = False
    save_settings(settings)
    get_midpoint_settings(force_reload=True)

    positions = {"Sun": 0.0, "Mean Node": 120.0, "Moon": 60.0}
    with_nodes = compute_midpoints(positions, include_nodes=True)
    without_nodes = compute_midpoints(positions, include_nodes=False)

    assert any("Mean Node" in part for pair in with_nodes for part in pair)
    assert all("Mean Node" not in part for pair in without_nodes for part in pair)
