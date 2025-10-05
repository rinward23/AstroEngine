from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest

from astroengine.analysis import find_lunations

pytest.importorskip("swisseph")
if not (os.environ.get("SE_EPHE_PATH") or os.environ.get("SWE_EPH_PATH")):
    pytest.skip("Swiss ephemeris not available", allow_module_level=True)


def test_find_lunations_wrapper_orders_events() -> None:
    start = datetime(2025, 9, 1, tzinfo=UTC)
    end = datetime(2025, 10, 1, tzinfo=UTC)
    events = find_lunations(start, end)
    assert len(events) >= 3
    timestamps = [event.ts for event in events]
    assert timestamps == sorted(timestamps)
