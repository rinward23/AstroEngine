from datetime import datetime, timezone

from astroengine.atlas.tz import (
    from_utc,
    is_ambiguous,
    is_nonexistent,
    to_utc,
    tzid_for,
)

NYC = (40.7128, -74.0060)
LON = (51.5074, -0.1278)


def test_tzid_basic():
    assert tzid_for(*NYC) in ("America/New_York", "US/Eastern")
    assert tzid_for(*LON) == "Europe/London"


# Fall-back ambiguity (US): Nov 2, 2025 01:30 occurs twice
def test_ambiguous_fall_back():
    dt = datetime(2025, 11, 2, 1, 30)
    tzid = tzid_for(*NYC)
    assert is_ambiguous(dt, tzid)
    early = to_utc(dt, *NYC, policy="earliest")
    late = to_utc(dt, *NYC, policy="latest")
    assert (late - early).total_seconds() == 3600


# Spring-forward gap (US): Mar 9, 2025 02:30 nonexistent
def test_nonexistent_spring_forward_shift():
    dt = datetime(2025, 3, 9, 2, 30)
    tzid = tzid_for(*NYC)
    assert is_nonexistent(dt, tzid)
    u = to_utc(dt, *NYC, policy="shift_forward")
    lt = from_utc(u, *NYC)
    assert lt.hour >= 3


def test_round_trip():
    u = datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc)
    lt = from_utc(u, *NYC)
    back = to_utc(lt.replace(tzinfo=None), *NYC)
    assert back == u
