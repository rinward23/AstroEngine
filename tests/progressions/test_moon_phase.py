from __future__ import annotations

from dataclasses import dataclass

from astroengine.engine.progressions.moon_phase import PhaseInfo, progressed_phase
from astroengine.providers.swisseph_adapter import SE_MOON, SE_SUN


@dataclass
class DummySample:
    longitude: float


@dataclass
class DummyEphemeris:
    sun: float
    moon: float

    def sample(self, body: int, moment: object) -> DummySample:  # pragma: no cover - body unused
        if body == SE_SUN:
            return DummySample(self.sun)
        if body == SE_MOON:
            return DummySample(self.moon)
        raise AssertionError("unexpected body id")


def test_progressed_phase_returns_angle_and_name() -> None:
    ephem = DummyEphemeris(sun=10.0, moon=100.0)
    phase = progressed_phase(ephem, object())
    assert isinstance(phase, PhaseInfo)
    assert phase.angle_deg == 90.0
    assert phase.phase_name == "First Quarter"
    assert phase.octile_index == 2
