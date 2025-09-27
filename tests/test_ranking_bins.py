from datetime import datetime, timedelta, timezone

from astroengine.core.aspects_plus.aggregate import day_bins, paginate, rank_hits
from astroengine.core.aspects_plus.scan import Hit

PROFILE = {"weights": {"sextile": 0.6, "square": 0.9}}


def mk_hit(dt: datetime, orb: float, angle: float = 60.0) -> Hit:
    return Hit(
        a="Mars",
        b="Venus",
        aspect_angle=angle,
        exact_time=dt,
        orb=orb,
        orb_limit=3.0,
    )


def test_rank_hits_and_ordering():
    t0 = datetime(2025, 1, 1, tzinfo=timezone.utc)
    hits = [mk_hit(t0 + timedelta(hours=2), 0.5), mk_hit(t0 + timedelta(hours=1), 0.1)]

    ranked_time = rank_hits(hits, PROFILE, order_by="time")
    assert ranked_time[0]["exact_time"] == t0 + timedelta(hours=1)

    ranked_sev = rank_hits(hits, PROFILE, order_by="severity")
    assert ranked_sev[0]["severity"] >= ranked_sev[1]["severity"]

    ranked_orb = rank_hits(hits, PROFILE, order_by="orb")
    assert ranked_orb[0]["orb"] <= ranked_orb[1]["orb"]


def test_day_bins_and_pagination():
    t0 = datetime(2025, 1, 1, 10, tzinfo=timezone.utc)
    hits = [
        mk_hit(t0, 0.1),
        mk_hit(t0 + timedelta(hours=3), 0.2),
        mk_hit(t0 + timedelta(days=1), 0.3),
    ]
    ranked = rank_hits(hits, PROFILE)
    bins = day_bins(ranked)

    assert bins[0]["date"] == "2025-01-01" and bins[0]["count"] == 2
    assert bins[1]["date"] == "2025-01-02" and bins[1]["count"] == 1
    assert bins[0]["score"] is not None and bins[0]["score"] >= bins[1]["score"]

    page, total = paginate(ranked, limit=2, offset=0)
    assert total == 3 and len(page) == 2


def test_day_bins_handles_missing_severity():
    day = datetime(2025, 5, 1, 9, tzinfo=timezone.utc)
    hits = [
        {"exact_time": day, "severity": 0.4},
        {"exact_time": day + timedelta(hours=1), "severity": None},
        {"exact_time": day + timedelta(hours=2)},
    ]
    bins = day_bins(hits)
    assert bins == [{"date": "2025-05-01", "count": 3, "score": 0.4}]


def test_paginate_rejects_negative_values():
    ranked = rank_hits([mk_hit(datetime(2025, 1, 1, tzinfo=timezone.utc), 0.2)], PROFILE)
    try:
        paginate(ranked, limit=-1, offset=0)
    except ValueError:
        pass
    else:
        raise AssertionError("negative limit must raise ValueError")
