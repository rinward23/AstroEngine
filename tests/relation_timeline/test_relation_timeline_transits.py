from __future__ import annotations

import datetime as dt

from astroengine.relation_timeline import (
    TimelineRequest,
    compute_relationship_timeline,
)


def test_transit_square_detection(linear_ephemeris, body_ids, timeline_epoch) -> None:
    request = TimelineRequest(
        chart_type="Composite",
        positions={"Sun": 50.0},
        range_start=timeline_epoch,
        range_end=timeline_epoch + dt.timedelta(days=220),
        transiters=("Mars",),
        targets=("Sun",),
        aspects=(90,),
    )

    result = compute_relationship_timeline(
        request, adapter=linear_ephemeris, body_ids=body_ids
    )

    events = [event for event in result.events if event.type == "transit"]
    assert len(events) == 1
    event = events[0]

    expected_exact = timeline_epoch + dt.timedelta(days=162, hours=12)
    assert abs((event.exact_utc - expected_exact).total_seconds()) < 3600
    assert event.target == "Sun"
    assert event.aspect == 90
    assert event.max_severity > 0.99
    assert result.summary.counts_by_aspect["90"] == 1
