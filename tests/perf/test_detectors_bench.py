from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable

import pytest

pytest.importorskip(
    "pytest_benchmark",
    reason="pytest-benchmark not installed; install extras with `pip install -e .[dev]`.",
)
pytest.importorskip(
    "swisseph",
    reason="Install with `.[providers]` or set SE_EPHE_PATH/SWE_EPH_PATH to point at Swiss Ephemeris data.",
)

from astroengine.detectors.eclipses import find_eclipses
from astroengine.detectors.lunations import find_lunations
from astroengine.detectors.out_of_bounds import find_out_of_bounds
from astroengine.detectors.stations import find_shadow_periods, find_stations
from astroengine.detectors.ingresses import find_sign_ingresses
from astroengine.detectors.common import iso_to_jd
from astroengine.ephemeris import cache as ephe_cache

pytestmark = [pytest.mark.perf, pytest.mark.swiss]

_BASELINE_ARTIFACT = (
    Path(__file__).resolve().parents[2]
    / "qa"
    / "artifacts"
    / "benchmarks"
    / "detectors"
    / "2025-10-02.json"
)
_ALLOWED_SLOWDOWN = 1.25


def _have_swiss() -> bool:
    return bool(os.getenv("SE_EPHE_PATH") or os.getenv("SWE_EPH_PATH"))


pytestmark.append(
    pytest.mark.skipif(
        not _have_swiss(),
        reason="Swiss ephemeris path not configured (set SE_EPHE_PATH or SWE_EPH_PATH)",
    )
)


@pytest.fixture(scope="session")
def detector_latency_budgets() -> dict[str, dict[str, float]]:
    raw = json.loads(_BASELINE_ARTIFACT.read_text(encoding="utf-8"))
    metrics = raw.get("metrics", {})
    budgets: dict[str, dict[str, float]] = {}
    for key, values in metrics.items():
        mean_seconds = float(values["mean_seconds"])
        median_seconds = float(values["median_seconds"])
        budgets[key] = {
            "mean": mean_seconds * _ALLOWED_SLOWDOWN,
            "median": median_seconds * _ALLOWED_SLOWDOWN,
        }
    if not budgets:
        raise RuntimeError(f"No detector metrics found in {_BASELINE_ARTIFACT}")
    return budgets


def _reset_ephemeris_cache() -> None:
    ephe_cache.calc_ut_cached.cache_clear()
    ephe_cache.julday_cached.cache_clear()


_START_ISO = "2025-01-01T00:00:00Z"
_END_ISO = "2025-12-31T23:59:59Z"
_START_JD = iso_to_jd(_START_ISO)
_END_JD = iso_to_jd(_END_ISO)

_STATION_BODIES = ("mercury", "venus", "mars", "jupiter", "saturn")
_SHADOW_BODIES = ("mercury", "venus")
_SIGN_BODIES = ("sun", "mercury", "venus", "mars", "jupiter", "saturn")
_OOB_BODIES = ("moon", "mercury", "venus", "mars")


def _run_stations():
    _reset_ephemeris_cache()
    return find_stations(_START_JD, _END_JD, bodies=_STATION_BODIES)


def _run_shadow():
    _reset_ephemeris_cache()
    return find_shadow_periods(_START_JD, _END_JD, bodies=_SHADOW_BODIES)


def _run_sign_ingresses():
    _reset_ephemeris_cache()
    return find_sign_ingresses(_START_JD, _END_JD, bodies=_SIGN_BODIES)


def _run_lunations():
    _reset_ephemeris_cache()
    return find_lunations(_START_JD, _END_JD)


def _run_eclipses():
    _reset_ephemeris_cache()
    return find_eclipses(_START_JD, _END_JD)


def _run_out_of_bounds():
    _reset_ephemeris_cache()
    return find_out_of_bounds(_START_JD, _END_JD, bodies=_OOB_BODIES)


DetectorRunner = Callable[[], list]

_DETECTOR_CASES: tuple[tuple[str, DetectorRunner], ...] = (
    ("find_stations", _run_stations),
    ("find_shadow_periods", _run_shadow),
    ("find_sign_ingresses", _run_sign_ingresses),
    ("find_lunations", _run_lunations),
    ("find_eclipses", _run_eclipses),
    ("find_out_of_bounds", _run_out_of_bounds),
)


@pytest.mark.benchmark(group="detectors")
@pytest.mark.parametrize("detector_key, runner", _DETECTOR_CASES)
def test_detector_latency(detector_key: str, runner: DetectorRunner, benchmark, detector_latency_budgets):
    result = benchmark(runner)
    stats = dict(benchmark.stats)
    budget = detector_latency_budgets[detector_key]

    assert stats["mean"] <= budget["mean"], (
        f"{detector_key} mean latency {stats['mean']:.3f}s exceeded budget {budget['mean']:.3f}s"
    )
    assert stats["median"] <= budget["median"], (
        f"{detector_key} median latency {stats['median']:.3f}s exceeded budget {budget['median']:.3f}s"
    )
    assert isinstance(result, list)
    assert result, f"{detector_key} did not produce any events"
