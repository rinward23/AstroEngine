from __future__ import annotations

import datetime as dt
import math

from astroengine.relation_timeline import (
    TimelineRequest,
    compute_relationship_timeline,
)


def test_return_detection_has_precise_window(
    linear_ephemeris, body_ids, timeline_epoch
) -> None:
    request = TimelineRequest(
        chart_type="Composite",
        positions={"Venus": 10.0},
        range_start=timeline_epoch,
        range_end=timeline_epoch + dt.timedelta(days=30),
        transiters=("Venus",),
        targets=(),
        aspects=(0,),
    )

    result = compute_relationship_timeline(
        request, adapter=linear_ephemeris, body_ids=body_ids
    )

    returns = [event for event in result.events if event.type == "return"]
    assert len(returns) == 1

    event = returns[0]
    expected_exact = timeline_epoch + dt.timedelta(days=10)
    assert abs((event.exact_utc - expected_exact).total_seconds()) < 120

    # Base orb for Venus is 3°, motion 1°/day, so window spans ~6 days.
    expected_start = timeline_epoch + dt.timedelta(days=7)
    expected_end = timeline_epoch + dt.timedelta(days=13)
    assert abs((event.start_utc - expected_start).total_seconds()) < 7200
    assert abs((event.end_utc - expected_end).total_seconds()) < 7200

    assert math.isclose(event.orb, 3.0, rel_tol=1e-6)
    assert event.max_severity > 0.99
    assert result.summary.counts_by_transiter["Venus"] == 1
