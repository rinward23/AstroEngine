from __future__ import annotations

import datetime as dt

from astroengine.relation_timeline import (
    TimelineRequest,
    compute_relationship_timeline,
)


def test_exports_include_all_fields(linear_ephemeris, body_ids, timeline_epoch) -> None:
    request = TimelineRequest(
        chart_type="Composite",
        positions={"Venus": 10.0},
        range_start=timeline_epoch,
        range_end=timeline_epoch + dt.timedelta(days=40),
        transiters=("Venus",),
        targets=(),
        aspects=(0,),
    )

    result = compute_relationship_timeline(
        request, adapter=linear_ephemeris, body_ids=body_ids
    )

    assert result.csv.startswith("type,chart,transiter")
    assert "return,Composite,Venus" in result.csv

    assert "BEGIN:VCALENDAR" in result.ics
    assert "Return Venus (Composite)" in result.ics
    assert "END:VCALENDAR" in result.ics
