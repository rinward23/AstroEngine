from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from astroengine.api._time import ensure_utc_datetime
from astroengine.api.routers.scan import TimeWindow
from astroengine.api.schemas_traditional import TraditionalChartInput


def test_ensure_utc_datetime_normalizes_offset_string() -> None:
    moment = ensure_utc_datetime("2025-11-02T01:30:00-04:00")
    assert moment.tzinfo is UTC
    assert moment.hour == 5 and moment.minute == 30


def test_ensure_utc_datetime_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError):
        ensure_utc_datetime(datetime(2025, 11, 2, 1, 30))


def test_ensure_utc_datetime_rejects_leap_second() -> None:
    with pytest.raises(ValueError):
        ensure_utc_datetime("2016-12-31T23:59:60Z")


def test_timewindow_rejects_naive_strings() -> None:
    with pytest.raises(ValidationError):
        TimeWindow(
            natal="2025-01-01T00:00:00",
            start="2025-01-01T00:00:00",
            end="2025-01-02T00:00:00",
        )


def test_traditional_chart_input_normalizes_to_utc() -> None:
    payload = TraditionalChartInput(
        moment="2025-03-30T02:15:00+01:00",
        latitude=40.0,
        longitude=-74.0,
    )
    assert payload.moment.tzinfo is UTC
    assert payload.moment.hour == 1 and payload.moment.minute == 15
