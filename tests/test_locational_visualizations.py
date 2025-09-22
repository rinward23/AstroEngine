from datetime import datetime, timezone

import pytest

from astroengine.ux.maps import astrocartography_lines, local_space_vectors
from astroengine.ux.timelines import outer_cycle_windows


def _moment() -> datetime:
    return datetime(2020, 12, 21, 13, 0, tzinfo=timezone.utc)


def test_astrocartography_lines_basic() -> None:
    pytest.importorskip("swisseph")
    lines = astrocartography_lines(_moment(), bodies=["jupiter"], lat_step=30.0)
    assert any(line.body == "jupiter" and line.kind == "MC" for line in lines)
    mc_line = next(line for line in lines if line.body == "jupiter" and line.kind == "MC")
    assert len(mc_line.coordinates) > 0
    assert all(-90.0 <= lat <= 90.0 for _, lat in mc_line.coordinates)


def test_local_space_vectors_range() -> None:
    pytest.importorskip("swisseph")
    vectors = local_space_vectors(_moment(), 40.7128, -74.0060, bodies=["sun"])
    assert len(vectors) == 1
    vector = vectors[0]
    assert -90.0 <= vector.altitude_deg <= 90.0
    assert 0.0 <= vector.azimuth_deg <= 360.0


def test_outer_cycle_windows_detects_conjunction() -> None:
    pytest.importorskip("swisseph")
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    end = datetime(2021, 1, 1, tzinfo=timezone.utc)
    windows = outer_cycle_windows(
        start,
        end,
        bodies=("jupiter", "saturn"),
        aspects={0.0: "conjunction"},
        step_days=1.0,
        orb_allow=1.0,
    )
    assert windows
    assert any("conjunction" in (window.metadata or {}).get("aspect", "") for window in windows)
