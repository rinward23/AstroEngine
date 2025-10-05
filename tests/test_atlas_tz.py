from datetime import datetime, timezone


import pytest


from astroengine.atlas.tz import (
    from_utc,
    is_ambiguous,
    is_nonexistent,
    to_utc,
    tzid_for,
)

NYC = (40.7128, -74.0060)
LON = (51.5074, -0.1278)
SYD = (-33.8688, 151.2093)


def test_tzid_basic():

    assert tzid_for(*NYC) in {"America/New_York", "US/Eastern"}
    assert tzid_for(*LON) == "Europe/London"



def test_ambiguous_fall_back():
    dt = datetime(2025, 11, 2, 1, 30)
    tzid = tzid_for(*NYC)
    assert is_ambiguous(dt, tzid)
    early = to_utc(dt, *NYC, ambiguous="earliest")
    late = to_utc(dt, *NYC, ambiguous="latest")
    assert (late.utc - early.utc).total_seconds() == 3600
    assert early.fold == 0 and late.fold == 1
    assert early.tzid == tzid == late.tzid
    assert early.local.tzinfo is not None and getattr(early.local.tzinfo, "key", tzid) == tzid
    assert late.local.fold == 1




def test_nonexistent_spring_forward_shift():
    dt = datetime(2025, 3, 9, 2, 30)
    tzid = tzid_for(*NYC)
    assert is_nonexistent(dt, tzid)

    shifted = to_utc(dt, *NYC, nonexistent="post")
    assert shifted.nonexistent and shifted.gap is not None
    assert shifted.gap.total_seconds() == 3600
    local = from_utc(shifted.utc, *NYC)
    assert local.hour >= 3


def test_round_trip():
    utc_dt = datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc)
    local = from_utc(utc_dt, *NYC)
    round_tripped = to_utc(local.replace(tzinfo=None), *NYC)
    assert round_tripped.utc == utc_dt


def test_policy_raise_for_nonexistent():
    dt = datetime(2025, 3, 9, 2, 30)
    with pytest.raises(ValueError):
        to_utc(dt, *NYC, nonexistent="raise")


def test_policy_raise_for_ambiguous():
    dt = datetime(2025, 11, 2, 1, 30)
    with pytest.raises(ValueError):
        to_utc(dt, *NYC, ambiguous="raise")


def test_to_utc_ambiguous_golden_values():
    dt = datetime(2025, 11, 2, 1, 30)
    earliest = to_utc(dt, *NYC, ambiguous="earliest")
    latest = to_utc(dt, *NYC, ambiguous="latest")
    assert earliest.utc == datetime(2025, 11, 2, 5, 30, tzinfo=timezone.utc)
    assert latest.utc == datetime(2025, 11, 2, 6, 30, tzinfo=timezone.utc)


def test_to_utc_shift_forward_golden_value():
    dt = datetime(2025, 3, 9, 2, 30)
    shifted = to_utc(dt, *NYC, nonexistent="post")
    assert shifted.utc == datetime(2025, 3, 9, 7, 30, tzinfo=timezone.utc)


def test_to_utc_pre_gap_policy():
    dt = datetime(2025, 3, 9, 2, 30)
    pre_policy = to_utc(dt, *NYC, nonexistent="pre")
    assert pre_policy.nonexistent
    assert pre_policy.utc == datetime(2025, 3, 9, 6, 30, tzinfo=timezone.utc)


def test_to_utc_flagged_ambiguous():
    dt = datetime(2025, 11, 2, 1, 15)
    flagged = to_utc(dt, *NYC, ambiguous="flag")
    assert flagged.ambiguous
    assert flagged.ambiguous_flagged
    assert flagged.fold == 0


@pytest.mark.parametrize(
    "coords,local_expected,utc_expected",
    [
        (
            NYC,
            datetime(2021, 3, 14, 2, 0),
            datetime(2021, 3, 14, 7, 0, tzinfo=timezone.utc),
        ),
        (
            LON,
            datetime(2021, 3, 28, 1, 30),
            datetime(2021, 3, 28, 1, 30, tzinfo=timezone.utc),
        ),
        (
            SYD,
            datetime(2021, 10, 3, 2, 30),
            datetime(2021, 10, 2, 16, 30, tzinfo=timezone.utc),
        ),
    ],
)
def test_dst_birth_nonexistent_windows(coords, local_expected, utc_expected):
    tzid = tzid_for(*coords)
    assert is_nonexistent(local_expected, tzid)
    shifted = to_utc(local_expected, *coords, policy="shift_forward")
    assert shifted == utc_expected


@pytest.mark.parametrize(
    "coords,local_time,earliest_expected,latest_expected",
    [
        (
            NYC,
            datetime(2021, 11, 7, 1, 30),
            datetime(2021, 11, 7, 5, 30, tzinfo=timezone.utc),
            datetime(2021, 11, 7, 6, 30, tzinfo=timezone.utc),
        ),
        (
            LON,
            datetime(2021, 10, 31, 1, 30),
            datetime(2021, 10, 31, 0, 30, tzinfo=timezone.utc),
            datetime(2021, 10, 31, 1, 30, tzinfo=timezone.utc),
        ),
        (
            SYD,
            datetime(2021, 4, 4, 2, 30),
            datetime(2021, 4, 3, 15, 30, tzinfo=timezone.utc),
            datetime(2021, 4, 3, 16, 30, tzinfo=timezone.utc),
        ),
    ],
)
def test_dst_birth_ambiguous_windows(coords, local_time, earliest_expected, latest_expected):
    tzid = tzid_for(*coords)
    assert is_ambiguous(local_time, tzid)
    earliest = to_utc(local_time, *coords, policy="earliest")
    latest = to_utc(local_time, *coords, policy="latest")
    assert earliest == earliest_expected
    assert latest == latest_expected
    assert (latest - earliest).total_seconds() == 3600


