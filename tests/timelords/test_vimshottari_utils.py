from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from astroengine.chart import ChartLocation
from astroengine.timelords import context as context_module
from astroengine.timelords import zodiacal
from astroengine.timelords.models import TimelordStack
from astroengine.timelords.vimshottari import generate_vimshottari_periods
from astroengine.timelords.zodiacal import generate_zodiacal_releasing


class DummyAdapter:
    def __init__(self, base_moment: datetime, base_jd: float) -> None:
        self.base_moment = base_moment
        self.base_jd = base_jd

    def ayanamsa(self, _jd: float) -> float:
        return 0.0

    def julian_day(self, moment: datetime) -> float:
        delta = (moment - self.base_moment).total_seconds() / 86400.0
        return self.base_jd + delta


def _stub_context() -> context_module.TimelordContext:
    base_moment = datetime(2000, 1, 1, 12, tzinfo=UTC)
    base_jd = 2451545.0
    adapter = DummyAdapter(base_moment, base_jd)
    chart = SimpleNamespace(
        julian_day=base_jd,
        houses=SimpleNamespace(ascendant=15.0),
        positions={
            "Sun": SimpleNamespace(longitude=20.0),
            "Moon": SimpleNamespace(longitude=80.0),
        },
    )
    location = ChartLocation(latitude=0.0, longitude=0.0)
    return context_module.TimelordContext(
        moment=base_moment,
        location=location,
        chart=chart,
        adapter=adapter,
    )


def test_build_context_normalizes_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class StubAdapter:
        def __init__(self) -> None:
            captured["adapter"] = self

    def fake_compute(moment: datetime, location: ChartLocation, adapter: StubAdapter) -> object:
        captured["moment"] = moment
        captured["location"] = location
        captured["compute_adapter"] = adapter
        return SimpleNamespace()

    monkeypatch.setattr(context_module, "SwissEphemerisAdapter", StubAdapter)
    monkeypatch.setattr(context_module, "compute_natal_chart", fake_compute)

    local = datetime(2020, 1, 1, 12, tzinfo=timezone(timedelta(hours=2)))
    ctx = context_module.build_context(local, 51.5, -0.1)

    assert ctx.moment.tzinfo is UTC
    assert ctx.moment.hour == 10
    assert captured["moment"].tzinfo is UTC
    assert isinstance(captured["location"], ChartLocation)
    assert captured["compute_adapter"] is captured["adapter"]


def test_generate_timelines_serialization() -> None:
    context = _stub_context()
    until = context.moment + timedelta(days=400)

    vim_periods = generate_vimshottari_periods(context, until, levels=2)
    assert vim_periods, "expected Vimśottarī periods to be generated"
    assert vim_periods[0].metadata.get("nakshatra")

    zr_periods = generate_zodiacal_releasing(context, context.moment + timedelta(days=200), levels=2)
    assert zr_periods, "expected zodiacal releasing periods"
    assert zr_periods[0].metadata["sign"] in zodiacal.ZODIAC_SIGNS

    serialised = vim_periods[0].to_dict()
    assert serialised["system"] == "vimshottari"
    assert serialised["start"].endswith("Z")
    assert serialised["end"].endswith("Z")
    assert serialised["metadata"] is not vim_periods[0].metadata

    stack = TimelordStack(moment=context.moment, periods=tuple(vim_periods[:2]))
    payload = stack.to_dict()
    assert payload["moment"].endswith("Z")
    assert payload["periods"][0]["start"].endswith("Z")
    assert payload["periods"][0]["system"] == "vimshottari"

    with pytest.raises(ValueError):
        generate_vimshottari_periods(context, until, levels=0)

    with pytest.raises(ValueError):
        generate_vimshottari_periods(context, until, levels=6)
