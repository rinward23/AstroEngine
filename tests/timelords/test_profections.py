from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from astroengine.chart import ChartLocation
from astroengine.timelords import context as context_module
from astroengine.timelords import profections
from astroengine.timelords.context import TimelordContext
from astroengine.timelords.models import TimelordPeriod


def _stub_context(moment: datetime | None = None, asc: float = 15.0) -> TimelordContext:
    base_moment = moment or datetime(2000, 1, 1, tzinfo=UTC)
    chart = SimpleNamespace(houses=SimpleNamespace(ascendant=asc))
    adapter = SimpleNamespace()
    location = ChartLocation(latitude=0.0, longitude=0.0)
    return TimelordContext(moment=base_moment, location=location, chart=chart, adapter=adapter)


def test_generate_profection_periods_rotates_houses_across_levels() -> None:
    context = _stub_context()
    until = context.moment + timedelta(days=370)
    periods = profections.generate_profection_periods(context, until)

    annual = [period for period in periods if period.level == "annual"]
    assert [entry.metadata["house"] for entry in annual[:2]] == [1, 2]
    assert [entry.metadata["sign"] for entry in annual[:2]] == ["aries", "taurus"]

    monthly = [period for period in periods if period.level == "monthly"]
    assert [entry.metadata["house"] for entry in monthly[:12]] == list(range(1, 13))
    assert monthly[12].metadata["house"] == 2
    assert monthly[0].metadata["sign"] == "aries"

    daily = [period for period in periods if period.level == "daily"]
    assert daily[0].metadata["house"] == 1
    assert daily[0].metadata["sign"] == "aries"
    assert daily[-1].end > daily[-1].start


def test_generate_profection_periods_respects_ascendant_offset() -> None:
    context = _stub_context(asc=95.0)
    until = context.moment + timedelta(days=400)
    periods = profections.generate_profection_periods(context, until)

    annual = [period for period in periods if period.level == "annual"]
    assert annual[0].metadata["sign"] == "cancer"
    assert annual[1].metadata["sign"] == "leo"

    monthly = [period for period in periods if period.level == "monthly"]
    assert monthly[0].metadata["sign"] == "cancer"
    assert monthly[1].metadata["sign"] == "leo"


def test_annual_profections_filters_events_and_ignores_non_annual(monkeypatch: pytest.MonkeyPatch) -> None:
    start = datetime(2000, 1, 1, tzinfo=UTC)
    later = start + timedelta(days=365)

    periods = [
        TimelordPeriod(
            system="profections",
            level="annual",
            ruler="mars",
            start=start - timedelta(days=400),
            end=start - timedelta(days=200),
            metadata={"house": 12, "sign": "pisces"},
        ),
        TimelordPeriod(
            system="profections",
            level="annual",
            ruler="venus",
            start=start,
            end=later,
            metadata={"house": 1, "sign": "aries"},
        ),
        TimelordPeriod(
            system="profections",
            level="monthly",
            ruler="mars",
            start=start,
            end=start + timedelta(days=30),
            metadata={"house": 1, "sign": "aries"},
        ),
    ]

    class DummyAdapter:
        def julian_day(self, moment: datetime) -> float:
            return 2451545.0 + (moment - start).total_seconds() / 86400.0

    def fake_build_context(natal_moment: datetime, lat: float, lon: float) -> TimelordContext:
        return TimelordContext(
            moment=natal_moment,
            location=ChartLocation(latitude=lat, longitude=lon),
            chart=SimpleNamespace(),
            adapter=DummyAdapter(),
        )

    monkeypatch.setattr(context_module, "build_context", fake_build_context)
    monkeypatch.setattr(profections, "_profection_periods", lambda _context, _until: periods)

    events = profections.annual_profections(
        natal_ts="1990-01-01T00:00:00Z",
        start_ts=start.isoformat().replace("+00:00", "Z"),
        end_ts=(start + timedelta(days=10)).isoformat().replace("+00:00", "Z"),
        lat=10.0,
        lon=20.0,
    )

    assert len(events) == 1
    event = events[0]
    assert event.house == 1
    assert event.ruler == "venus"
    assert event.method == "annual"
    assert event.ts.endswith("Z")
    assert event.midpoint_ts.endswith("Z")

    empty = profections.annual_profections(
        natal_ts="1990-01-01T00:00:00Z",
        start_ts=start.isoformat().replace("+00:00", "Z"),
        end_ts=start.isoformat().replace("+00:00", "Z"),
        lat=10.0,
        lon=20.0,
    )
    assert empty == []
