# >>> AUTO-GEN BEGIN: tests-lunations v1.0
from __future__ import annotations

import os

import pytest

try:
    HAVE_SWISS = True
except Exception:
    HAVE_SWISS = False

SE_OK = bool(os.environ.get("SE_EPHE_PATH") or os.environ.get("SWE_EPH_PATH"))

pytestmark = pytest.mark.skipif(
    not (HAVE_SWISS and SE_OK), reason="Swiss ephemeris not available"
)

from datetime import UTC

from astroengine.detectors.common import UNIX_EPOCH_JD
from astroengine.detectors.lunations import find_lunations


def iso_to_jd(iso_ts: str) -> float:
    from datetime import datetime

    dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00")).astimezone(UTC)
    return (dt.timestamp() / 86400.0) + UNIX_EPOCH_JD


def test_lunations_count_and_order():
    # September 2025 window
    start = iso_to_jd("2025-09-01T00:00:00Z")
    end = iso_to_jd("2025-10-01T00:00:00Z")
    ev = find_lunations(start, end)
    assert len(ev) >= 3
    # strictly increasing timestamps
    ts = [e.ts for e in ev]
    assert ts == sorted(ts)


# >>> AUTO-GEN END: tests-lunations v1.0
