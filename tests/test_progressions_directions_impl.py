# >>> AUTO-GEN BEGIN: tests-prog-dir v1.0
from __future__ import annotations

import os

import pytest

from astroengine.detectors.directions import solar_arc_directions
from astroengine.detectors.progressions import secondary_progressions

try:  # pragma: no cover - optional dependency guard
    HAVE_SWISS = True
except Exception:  # pragma: no cover - defensive fallback
    HAVE_SWISS = False

SE_OK = bool(os.environ.get("SE_EPHE_PATH") or os.environ.get("SWE_EPH_PATH"))
pytestmark = pytest.mark.skipif(
    not (HAVE_SWISS and SE_OK), reason="Swiss ephemeris not available"
)


def test_secondary_progressions_annual_samples():
    natal = "1990-01-01T12:00:00Z"
    start = "2020-01-01T00:00:00Z"
    end = "2025-01-01T00:00:00Z"
    ev = secondary_progressions(natal, start, end)
    assert ev
    assert all(e.method == "secondary" for e in ev)


def test_solar_arc_directions_annual_samples():
    natal = "1990-01-01T12:00:00Z"
    start = "2020-01-01T00:00:00Z"
    end = "2025-01-01T00:00:00Z"
    ev = solar_arc_directions(natal, start, end)
    assert ev
    assert all(e.method == "solar_arc" for e in ev)


# >>> AUTO-GEN END: tests-prog-dir v1.0
