from __future__ import annotations

from datetime import UTC, datetime

import pytest

try:
    from astroengine.analysis import find_lunations
except ImportError as exc:  # pragma: no cover - depends on optional deps
    find_lunations = None  # type: ignore[assignment]
    _ANALYSIS_IMPORT_ERROR = exc
else:
    _ANALYSIS_IMPORT_ERROR = None

pytestmark = pytest.mark.swiss


def test_find_lunations_wrapper_orders_events() -> None:
    if find_lunations is None:
        pytest.skip(f"find_lunations unavailable: {_ANALYSIS_IMPORT_ERROR}")
    start = datetime(2025, 9, 1, tzinfo=UTC)
    end = datetime(2025, 10, 1, tzinfo=UTC)
    events = find_lunations(start, end)
    assert len(events) >= 3
    timestamps = [event.ts for event in events]
    assert timestamps == sorted(timestamps)
