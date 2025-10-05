from datetime import datetime, timedelta, timezone

import pytest

from astroengine.electional import ElectionalSearchParams, search_constraints
from astroengine.electional.solver import SampleContext
from astroengine.ephemeris import BodyPosition


class StubProvider:
    def __init__(self, contexts):
        self._contexts = contexts

    def context(self, ts: datetime) -> SampleContext:
        try:
            return self._contexts[ts]
        except KeyError as exc:  # pragma: no cover - defensive
            raise AssertionError(f"unexpected timestamp {ts!r}") from exc


def _body(name: str, lon: float) -> BodyPosition:
    return BodyPosition(
        body=name,
        julian_day=0.0,
        longitude=lon,
        latitude=0.0,
        distance_au=1.0,
        speed_longitude=0.0,
        speed_latitude=0.0,
        speed_distance=0.0,
        declination=0.0,
        speed_declination=0.0,
    )


def test_search_constraints_basic_match():
    t0 = datetime(2025, 1, 1, tzinfo=timezone.utc)
    t1 = t0 + timedelta(hours=1)

    context_ok = SampleContext(
        ts=t0,
        iso=t0.isoformat().replace("+00:00", "Z"),
        positions={
            "Venus": _body("Venus", 100.0),
            "Moon": _body("Moon", 10.0),
            "Sun": _body("Sun", 14.0),
            "Mars": _body("Mars", 210.0),
            "Saturn": _body("Saturn", 300.0),
        },
        axes={"asc": 340.0, "desc": 160.0, "mc": 250.0, "ic": 70.0},
    )

    context_miss = SampleContext(
        ts=t1,
        iso=t1.isoformat().replace("+00:00", "Z"),
        positions={
            "Venus": _body("Venus", 30.0),
            "Moon": _body("Moon", 40.0),
            "Sun": _body("Sun", 80.0),
            "Mars": _body("Mars", 210.0),
            "Saturn": _body("Saturn", 300.0),
        },
        axes={"asc": 340.0, "desc": 160.0, "mc": 250.0, "ic": 70.0},
    )

    provider = StubProvider({t0: context_ok, t1: context_miss})

    params = ElectionalSearchParams(
        start=t0,
        end=t1,
        step_minutes=60,
        constraints=[
            {"aspect": {"body": "venus", "target": "asc", "type": "trine", "max_orb": 1.0}},
            {"moon": {"void_of_course": False, "max_orb": 6.0}},
            {"malefic_to_angles": {"allow": False, "max_orb": 3.0}},
        ],
        latitude=0.0,
        longitude=0.0,
        limit=5,
    )

    results = search_constraints(params, provider=provider)
    assert len(results) == 1
    assert results[0].ts == t0
    assert results[0].score > 0
    assert all(ev.passed for ev in results[0].evaluations)


def test_search_constraints_finds_weighted_solutions_with_tolerance():
    t0 = datetime(2026, 3, 20, tzinfo=timezone.utc)
    t1 = t0 + timedelta(minutes=30)
    t2 = t1 + timedelta(minutes=30)

    def ctx(ts: datetime, venus: float, mars: float, sun: float) -> SampleContext:
        iso = ts.isoformat().replace("+00:00", "Z")
        return SampleContext(
            ts=ts,
            iso=iso,
            positions={
                "Venus": _body("Venus", venus),
                "Mars": _body("Mars", mars),
                "Sun": _body("Sun", sun),
            },
            axes={
                "asc": 30.0,
                "desc": 210.0,
                "mc": 120.0,
                "ic": 300.0,
            },
        )

    contexts = {
        t0: ctx(t0, venus=30.0, mars=150.0, sun=150.0),
        t1: ctx(t1, venus=30.3, mars=150.2, sun=150.4),
        t2: ctx(t2, venus=31.0, mars=152.0, sun=152.0),
    }

    provider = StubProvider(contexts)

    params = ElectionalSearchParams(
        start=t0,
        end=t2,
        step_minutes=30,
        constraints=[
            {
                "aspect": {
                    "body": "sun",
                    "target": "asc",
                    "type": "trine",
                    "max_orb": 0.5,
                }
            },
            {
                "antiscia": {
                    "body": "venus",
                    "target": "mars",
                    "type": "antiscia",
                    "axis": "cancer_capricorn",
                    "max_orb": 0.5,
                }
            },
        ],
        latitude=0.0,
        longitude=0.0,
        limit=3,
    )

    results = search_constraints(params, provider=provider)
    assert [candidate.ts for candidate in results] == [t0, t1]

    first = results[0]
    aspect_eval = next(ev for ev in first.evaluations if ev.constraint == "aspect")
    antiscia_eval = next(ev for ev in first.evaluations if ev.constraint == "antiscia")
    assert aspect_eval.detail["orb"] == pytest.approx(0.0, abs=1e-9)
    assert antiscia_eval.detail["orb"] == pytest.approx(0.0, abs=1e-9)
    assert first.score > 0

    second = results[1]
    aspect_eval = next(ev for ev in second.evaluations if ev.constraint == "aspect")
    antiscia_eval = next(ev for ev in second.evaluations if ev.constraint == "antiscia")
    assert 0.0 < aspect_eval.detail["orb"] <= 0.5
    assert 0.0 < antiscia_eval.detail["orb"] <= 0.5
    assert second.score > 0
