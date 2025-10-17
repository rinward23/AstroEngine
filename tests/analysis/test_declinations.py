from __future__ import annotations

from dataclasses import asdict
from types import SimpleNamespace
import math

import pandas as pd
import pytest

from astroengine.analysis import declinations as decl_mod
from astroengine.analysis.declinations import declination_aspects, get_declinations
from astroengine.astro.declination import ecl_to_dec
from astroengine.detectors import out_of_bounds as oob


class _ChartStub:
    def __init__(self, positions, julian_day: float = 2451545.0) -> None:
        self.positions = positions
        self.julian_day = julian_day
        self.metadata = {
            "zodiac": "tropical",
            "nodes_variant": "mean",
            "lilith_variant": "mean",
        }


def test_declinations_and_aspects_with_synthetic_ephemeris(monkeypatch: pytest.MonkeyPatch) -> None:
    chart = _ChartStub(
        {
            "Sun": SimpleNamespace(longitude=120.0, declination=16.1),
            "Mars": {"longitude": 45.0},
            "Venus": {"declination": 12.0},
            "Moon": {"longitude": None},
            "South Node": {"longitude": None},
        }
    )

    class _AdapterStub:
        def __init__(self) -> None:
            self._values = {"moon": -12.05, "south node": 12.5}

        def body_position(self, jd_ut: float, code: int, body_name: str | None = None):
            key = (body_name or "").lower()
            if key not in self._values:
                raise AssertionError(f"unexpected Swiss ephemeris lookup for {body_name}")
            return SimpleNamespace(declination=self._values[key])

    fake_adapter = _AdapterStub()

    decl_mod._adapter_for_chart.cache_clear()
    monkeypatch.setattr(decl_mod, "has_swe", lambda: True)
    monkeypatch.setattr(
        decl_mod,
        "get_swisseph",
        lambda: SimpleNamespace(MOON=1, MEAN_NODE=2, SE_MOON=1, SE_MEAN_NODE=2),
    )
    monkeypatch.setattr(decl_mod, "_adapter_for_chart", lambda *args, **kwargs: fake_adapter)

    declinations = get_declinations(chart)

    assert declinations["Sun"] == pytest.approx(16.1)
    assert declinations["Mars"] == pytest.approx(ecl_to_dec(45.0), abs=1e-6)
    assert declinations["Venus"] == pytest.approx(12.0)
    assert declinations["Moon"] == pytest.approx(-12.05)
    # South node declinations are negated when sourced via Swiss ephemeris.
    assert declinations["South Node"] == pytest.approx(-12.5)

    hits = declination_aspects(declinations, orb_deg=0.3)
    assert [hit.kind for hit in hits] == ["contraparallel", "parallel"]

    contra = hits[0]
    assert contra.body_a == "Moon"
    assert contra.body_b == "Venus"
    assert contra.orb == pytest.approx(0.05, abs=1e-3)

    parallel = hits[1]
    assert parallel.body_a == "Mars"
    assert parallel.body_b == "Sun"
    assert parallel.orb == pytest.approx(abs(declinations["Mars"] - declinations["Sun"]), abs=1e-6)


def test_out_of_bounds_dataframe_from_synthetic_samples(monkeypatch: pytest.MonkeyPatch) -> None:
    class _SweStub:
        MOON = 1
        ECL_NUT = 2
        FLG_SPEED = 0x1
        FLG_EQUATORIAL = 0x2

    start_jd = 2450000.0
    end_jd = start_jd + 1.0

    def _fake_calc_ut_cached(jd_ut: float, code: int, flag: int):
        if code == _SweStub.ECL_NUT:
            return ([23.5], 0)
        phase = math.pi * (jd_ut - start_jd)
        dec = 23.0 + math.sin(phase)
        speed_dec = math.pi * math.cos(phase)
        return ([0.0, dec, 0.0, 0.0, speed_dec], 0)

    monkeypatch.setattr(oob, "_HAS_SWE", True)
    monkeypatch.setattr(oob, "_BODY_CODES", {"moon": _SweStub.MOON})
    monkeypatch.setattr(oob, "swe", lambda: _SweStub)
    monkeypatch.setattr(oob, "init_ephe", lambda: 0)
    monkeypatch.setattr(oob, "calc_ut_cached", _fake_calc_ut_cached)

    events = oob.find_out_of_bounds(start_jd, end_jd, bodies=("Moon",), step_hours=6.0)

    assert len(events) == 2
    assert [event.state for event in events] == ["enter", "exit"]

    frame = pd.DataFrame(asdict(event) for event in events)
    assert list(frame.columns) == [
        "ts",
        "jd",
        "body",
        "state",
        "hemisphere",
        "declination",
        "limit",
    ]
    assert frame["body"].unique().tolist() == ["Moon"]
    assert set(frame["state"]) == {"enter", "exit"}
    assert pytest.approx(frame["declination"].abs().max(), rel=1e-3) == frame["limit"].iloc[0]
