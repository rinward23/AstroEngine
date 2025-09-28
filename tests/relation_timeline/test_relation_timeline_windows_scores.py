from __future__ import annotations

import datetime as dt

from astroengine.relation_timeline import (
    TimelineRequest,
    compute_relationship_timeline,
)


def test_scoring_and_series(linear_ephemeris, body_ids, timeline_epoch) -> None:
    request = TimelineRequest(
        chart_type="Davison",
        positions={"Node": 80.0},
        range_start=timeline_epoch,
        range_end=timeline_epoch + dt.timedelta(days=260),
        transiters=("Jupiter",),
        targets=("Node",),
        aspects=(0,),
        include_series=True,
    )

    result = compute_relationship_timeline(
        request, adapter=linear_ephemeris, body_ids=body_ids
    )

    event = result.events[0]
    assert event.type == "transit"
    assert event.series is not None
    assert event.series[0][0] == event.start_utc
    assert event.series[-1][0] == event.end_utc
    assert event.score > 0.0
    assert event.max_severity <= 1.0

    assert result.summary.total_score == event.score
    assert event.start_utc.date().isoformat() in result.summary.calendar
