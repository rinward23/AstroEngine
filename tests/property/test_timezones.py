from __future__ import annotations

import inspect
from datetime import datetime, timezone
from typing import Any

import pytest

hypothesis = pytest.importorskip("hypothesis")
given = hypothesis.given
settings = hypothesis.settings
st = hypothesis.strategies

atlas_tz = pytest.importorskip("astroengine.atlas.tz")
TO_UTC = getattr(atlas_tz, "to_utc")
FROM_UTC = getattr(atlas_tz, "from_utc")
_TO_UTC_PARAMS = inspect.signature(TO_UTC).parameters

COORDS = st.tuples(
    st.floats(min_value=-80.0, max_value=80.0, allow_nan=False, allow_infinity=False),
    st.floats(min_value=-179.9, max_value=179.9, allow_nan=False, allow_infinity=False),
)
INSTANTS = st.datetimes(
    min_value=datetime(1970, 1, 1, tzinfo=timezone.utc),
    max_value=datetime(2035, 12, 31, tzinfo=timezone.utc),
    timezones=st.just(timezone.utc),
)


def _ensure_datetime(value: Any) -> datetime:
    if isinstance(value, tuple | list):
        candidate = value[0]
    else:
        candidate = value
    if not isinstance(candidate, datetime):
        raise TypeError(f"Expected datetime from timezone helper, got {type(candidate)!r}")
    return candidate


def _call_from_utc(moment: datetime, lat: float, lon: float) -> datetime:
    try:
        local = FROM_UTC(moment, lat, lon)
    except TypeError:
        local = FROM_UTC(moment, latitude=lat, longitude=lon)
    return _ensure_datetime(local)


def _call_to_utc(moment: datetime, lat: float, lon: float, *, ambiguous: bool = False) -> datetime:
    kwargs: dict[str, Any] = {}
    if "policy" in _TO_UTC_PARAMS:
        kwargs.setdefault("policy", "shift_forward")
    if "nonexistent" in _TO_UTC_PARAMS:
        kwargs.setdefault("nonexistent", "shift_forward")
    if ambiguous and "ambiguous" in _TO_UTC_PARAMS:
        kwargs.setdefault("ambiguous", "earliest")
    try:
        utc_moment = TO_UTC(moment, lat, lon, **kwargs)
    except TypeError:
        utc_moment = TO_UTC(moment, latitude=lat, longitude=lon, **kwargs)
    return _ensure_datetime(utc_moment)


@settings(deadline=None)
@given(instant=INSTANTS, coords=COORDS)
def test_timezone_round_trip(instant: datetime, coords: tuple[float, float]) -> None:
    lat, lon = coords
    local = _call_from_utc(instant, lat, lon)
    local_naive = local.replace(tzinfo=None)
    back = _call_to_utc(local_naive, lat, lon)
    assert back == instant


def test_ambiguous_time_does_not_raise() -> None:
    lat, lon = 40.7128, -74.0060  # New York City
    ambiguous = datetime(2021, 11, 7, 1, 30)
    try:
        result = _call_to_utc(ambiguous, lat, lon, ambiguous=True)
    except Exception as exc:  # pragma: no cover - ensures explicit failure detail
        pytest.fail(f"Ambiguous local time should not raise, got {exc!r}")
    round_trip = _call_from_utc(result, lat, lon).replace(tzinfo=None)
    assert round_trip.hour in {1, 2, 3}


def test_nonexistent_time_shift_forward() -> None:
    lat, lon = 40.7128, -74.0060
    nonexistent = datetime(2021, 3, 14, 2, 30)
    result = _call_to_utc(nonexistent, lat, lon)
    local_after = _call_from_utc(result, lat, lon).replace(tzinfo=None)
    assert local_after > nonexistent
