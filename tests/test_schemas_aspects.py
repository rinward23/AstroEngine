from datetime import datetime
from app.schemas.aspects import (
    AspectSearchRequest, AspectSearchResponse, AspectHit, DayBin, TimeWindow, Paging
)


def test_request_minimal():
    req = AspectSearchRequest(
        objects=["Sun","Moon","Mars"],
        aspects=["square","trine"],
        window=TimeWindow(start=datetime.fromisoformat("2025-01-01T00:00:00+00:00"),
                          end=datetime.fromisoformat("2025-01-15T00:00:00+00:00")),
    )
    assert req.step_minutes == 60
    assert req.harmonics == []


def test_request_with_pairs_and_policy_inline():
    req = AspectSearchRequest(
        objects=["Mars","Venus"],
        aspects=["sextile"],
        harmonics=[5,7],
        pairs=[["Mars","Venus"]],
        window={"start":"2025-01-01T00:00:00+00:00","end":"2025-01-31T00:00:00+00:00"},
        orb_policy_inline={"per_aspect":{"sextile":3.0},"adaptive_rules":{"outers_factor":1.2}},
        step_minutes=15,
        limit=100,
        order_by="severity",
    )
    assert req.order_by == "severity"
    assert req.orb_policy_inline.per_aspect["sextile"] == 3.0


def test_response_example_shape():
    resp = AspectSearchResponse(
        hits=[
            AspectHit(
                a="Mars", b="Venus", aspect="sextile", harmonic=5,
                exact_time=datetime.fromisoformat("2025-02-14T08:12:00+00:00"),
                orb=0.12, orb_limit=3.0, severity=0.66,
            )
        ],
        bins=[DayBin(date=datetime(2025,2,14).date(), count=3, score=0.71)],
        paging=Paging(limit=200, offset=0, total=137),
    )
    js = resp.model_dump_json()
    assert "hits" in js and "paging" in js
