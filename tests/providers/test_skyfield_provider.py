"""Tests for the Skyfield ephemeris provider using stubbed loaders."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pytest

from astroengine.providers import skyfield_provider


@dataclass
class DummyTimescale:
    """Timescale stub that records UTC conversions."""

    utc_calls: list[tuple[int, int, int, int, int, float]]

    def utc(self, year: int, month: int, day: int, hour: int, minute: int, seconds: float):
        call = (year, month, day, hour, minute, seconds)
        self.utc_calls.append(call)
        return ("ts", call)


class DummyLoader:
    """Callable replacement for :func:`skyfield.api.load`."""

    def __init__(
        self,
        kernels: dict[str, object | Exception],
        timescale_factory: Callable[[], DummyTimescale | Exception],
    ) -> None:
        self.kernels = kernels
        self.timescale_factory = timescale_factory
        self.calls: list[str] = []
        self.timescale_calls = 0

    def __call__(self, name: str):
        self.calls.append(name)
        value = self.kernels.get(name)
        if value is None:
            raise OSError(f"kernel {name} missing")
        if isinstance(value, Exception):
            raise value
        return value

    def timescale(self):
        self.timescale_calls += 1
        result = self.timescale_factory()
        if isinstance(result, Exception):
            raise result
        return result


@pytest.fixture(autouse=True)
def restore_registration(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure provider registration globals do not leak between tests."""

    monkeypatch.setattr(skyfield_provider, "register_provider", lambda *args, **kwargs: None)
    monkeypatch.setattr(skyfield_provider, "register_provider_metadata", lambda *args, **kwargs: None)


def test_provider_initialization_with_kernel_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    kernel = object()
    loader = DummyLoader(
        kernels={
            "de440s.bsp": OSError("missing"),
            "de421.bsp": kernel,
        },
        timescale_factory=lambda: DummyTimescale(utc_calls=[]),
    )
    monkeypatch.setattr(skyfield_provider, "load", loader)

    provider = skyfield_provider.SkyfieldProvider()

    assert provider.kernel is kernel
    assert loader.calls == ["de440s.bsp", "de421.bsp"]
    assert loader.timescale_calls == 1
    assert isinstance(provider.ts, DummyTimescale)


def test_provider_timescale_initialization_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    loader = DummyLoader(
        kernels={"de440s.bsp": object()},
        timescale_factory=lambda: RuntimeError("timescale unavailable"),
    )
    monkeypatch.setattr(skyfield_provider, "load", loader)

    with pytest.raises(RuntimeError) as excinfo:
        skyfield_provider.SkyfieldProvider()

    assert "Failed to initialize skyfield timescale" in str(excinfo.value)
    assert loader.calls == ["de440s.bsp"]
    assert loader.timescale_calls == 1


def test_provider_raises_when_no_kernel_found(monkeypatch: pytest.MonkeyPatch) -> None:
    loader = DummyLoader(
        kernels={name: OSError("missing") for name in ("de440s.bsp", "de421.bsp", "de430t.bsp")},
        timescale_factory=lambda: DummyTimescale(utc_calls=[]),
    )
    monkeypatch.setattr(skyfield_provider, "load", loader)

    with pytest.raises(FileNotFoundError):
        skyfield_provider.SkyfieldProvider()

    assert loader.calls == ["de440s.bsp", "de421.bsp", "de430t.bsp"]


def test_provider_reuses_timescale_for_leap_seconds(monkeypatch: pytest.MonkeyPatch) -> None:
    timescale = DummyTimescale(utc_calls=[])
    loader = DummyLoader(
        kernels={"de440s.bsp": object()},
        timescale_factory=lambda: timescale,
    )
    monkeypatch.setattr(skyfield_provider, "load", loader)

    provider = skyfield_provider.SkyfieldProvider()

    provider._skyfield_time("2020-01-01T00:00:00Z")
    provider._skyfield_time("2020-01-01T01:00:00+00:00")

    assert loader.timescale_calls == 1
    assert timescale.utc_calls == [
        (2020, 1, 1, 0, 0, 0.0),
        (2020, 1, 1, 1, 0, 0.0),
    ]
