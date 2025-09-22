# >>> AUTO-GEN BEGIN: tests-stations v1.0
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

from astroengine.detectors.stations import find_stations
from astroengine.detectors.common import UNIX_EPOCH_JD


def iso_to_jd(iso_ts: str) -> float:
    from datetime import datetime, timezone
    dt = datetime.fromisoformat(iso_ts.replace('Z', '+00:00')).astimezone(timezone.utc)
    return (dt.timestamp()/86400.0) + UNIX_EPOCH_JD


def test_stations_basic():
    start = iso_to_jd("2025-01-01T00:00:00Z")
    end = iso_to_jd("2025-12-31T00:00:00Z")
    ev = find_stations(start, end)
    assert isinstance(ev, list)
    assert ev
# >>> AUTO-GEN END: tests-stations v1.0
