"""Shared fixtures for detector unit tests."""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Callable

import pytest

import astroengine.detectors.ingresses as ingresses
import astroengine.detectors.lunations as lunations
import astroengine.detectors.returns as returns
from astroengine.ephemeris import SwissEphemerisAdapter


class _FakeAdapter:
    """Deterministic Swiss ephemeris stand-in for detector tests."""

    def __init__(self, state: "_DetectorStubState") -> None:
        self._state = state
        self.is_sidereal = False
        self.body_position_calls: list[tuple[str, float]] = []
        self.julian_calls: list[datetime] = []

    def julian_day(self, moment: datetime) -> float:
        aware = moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)
        aware = aware.astimezone(UTC)
        self.julian_calls.append(aware)
        return self._state.origin + (aware.timestamp() / 86400.0)

    def body_position(self, jd: float, _body_code: int, *, body_name: str | None = None):
        name = (body_name or "").lower()
        longitude = self._state.body_lon(jd, name)
        speed = self._state.slopes.get(name, 0.0)
        self.body_position_calls.append((name or "", jd))
        return SimpleNamespace(longitude=longitude % 360.0, speed_longitude=speed)

    def body_positions(self, jd: float, body_map):  # type: ignore[override]
        return {
            name: self.body_position(jd, code, body_name=name)
            for name, code in body_map.items()
        }


class _DetectorStubState:
    """Stateful helpers injected into detector modules for repeatable tests."""

    def __init__(self) -> None:
        self.origin = 2451545.0
        self.slopes: dict[str, float] = {
            "sun": 40.0,
            "moon": 80.0,
            "mercury": 50.0,
            "venus": 30.0,
            "mars": 20.0,
            "jupiter": 10.0,
            "saturn": 5.0,
        }
        self.offsets: dict[str, float] = defaultdict(float)
        self._fail_intervals: set[tuple[float, float]] = set()
        self.adapter = _FakeAdapter(self)

    def set_linear(self, body: str, *, slope: float, offset: float = 0.0) -> None:
        self.slopes[body.lower()] = float(slope)
        self.offsets[body.lower()] = float(offset)

    def fail_between(self, left: float, right: float) -> None:
        key = (round(min(left, right), 6), round(max(left, right), 6))
        self._fail_intervals.add(key)

    def body_lon(self, jd: float, body: str | None) -> float:
        name = (body or "").lower()
        slope = self.slopes.get(name, 15.0)
        offset = self.offsets.get(name, 0.0)
        return offset + slope * (jd - self.origin)

    def solve(self, fn: Callable[[float], float], left: float, right: float, **_: object) -> float:
        a = float(min(left, right))
        b = float(max(left, right))
        key = (round(a, 6), round(b, 6))
        if key in self._fail_intervals:
            raise ValueError("forced zero-crossing failure")

        fa = fn(a)
        fb = fn(b)
        if math.isclose(fa, 0.0, abs_tol=1e-12):
            return a
        if math.isclose(fb, 0.0, abs_tol=1e-12):
            return b
        if fa * fb > 0:
            return (a + b) / 2.0

        for _ in range(48):
            mid = (a + b) / 2.0
            fm = fn(mid)
            if abs(fm) < 1e-9:
                return mid
            if fa * fm <= 0:
                b, fb = mid, fm
            else:
                a, fa = mid, fm
        return (a + b) / 2.0


@pytest.fixture(autouse=True)
def detector_stubs(monkeypatch: pytest.MonkeyPatch) -> _DetectorStubState:
    state = _DetectorStubState()

    monkeypatch.setattr(ingresses, "body_lon", state.body_lon)
    monkeypatch.setattr(ingresses, "solve_zero_crossing", state.solve)
    monkeypatch.setattr(ingresses, "_HAS_SWE", True)

    monkeypatch.setattr(lunations, "solve_zero_crossing", state.solve)
    monkeypatch.setattr(returns, "solve_zero_crossing", state.solve)

    monkeypatch.setattr(
        SwissEphemerisAdapter,
        "get_default_adapter",
        classmethod(lambda cls: state.adapter),
    )
    monkeypatch.setattr(
        SwissEphemerisAdapter,
        "from_chart_config",
        classmethod(lambda cls, *_args, **_kwargs: state.adapter),
    )

    return state
