# >>> AUTO-GEN BEGIN: tests-eclipses v1.0
from __future__ import annotations
import os
import pytest

try:
    import swisseph as swe  # type: ignore
    HAVE_SWISS = True
except Exception:
    HAVE_SWISS = False

SE_OK = bool(os.environ.get("SE_EPHE_PATH") or os.environ.get("SWE_EPH_PATH"))
pytestmark = pytest.mark.skipif(not (HAVE_SWISS and SE_OK), reason="Swiss ephemeris not available")

from astroengine.detectors.common import iso_to_jd
from astroengine.detectors.eclipses import find_eclipses


def test_eclipses_basic_window():
    start = iso_to_jd("2025-01-01T00:00:00Z")
    end = iso_to_jd("2025-12-31T00:00:00Z")
    ev = find_eclipses(start, end)
    assert isinstance(ev, list)
    assert ev
# >>> AUTO-GEN END: tests-eclipses v1.0
