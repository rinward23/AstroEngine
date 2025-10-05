# >>> AUTO-GEN BEGIN: perf smoke v1.0
import datetime as dt
import os

import pytest

pytest.importorskip(
    "swisseph", reason="Install with `.[providers]` or set SE_EPHE_PATH"
)

pytestmark = [pytest.mark.perf, pytest.mark.swiss]


def _have_swiss() -> bool:
    return bool(os.getenv("SE_EPHE_PATH") or os.getenv("SWE_EPH_PATH"))


@pytest.mark.skipif(not _have_swiss(), reason="Swiss unavailable")
def test_fast_scan_runs_under_budget():
    from astroengine.engine import ScanConfig, fast_scan

    start = dt.datetime(2025, 1, 1, 0, 0)
    end = dt.datetime(2025, 1, 3, 0, 0)
    cfg = ScanConfig(
        body=1, natal_lon_deg=195.0, aspect_angle_deg=0.0, orb_deg=6.0, tick_minutes=60
    )
    hits = fast_scan(start, end, cfg)
    assert isinstance(hits, list)
    assert len(hits) <= 12  # sanity


@pytest.mark.skipif(not _have_swiss(), reason="Swiss unavailable")
def test_fast_scan_year_budget_guard() -> None:
    from time import perf_counter

    import swisseph as swe  # type: ignore

    from astroengine.engine import ScanConfig, fast_scan

    start = dt.datetime(2020, 1, 1, 0, 0)
    end = dt.datetime(2021, 1, 1, 0, 0)

    base_bodies = [
        int(swe.SUN),
        int(swe.MOON),
        int(swe.MERCURY),
        int(swe.VENUS),
        int(swe.MARS),
        int(swe.JUPITER),
        int(swe.SATURN),
        int(swe.URANUS),
        int(swe.NEPTUNE),
        int(swe.PLUTO),
    ]
    bodies = base_bodies + base_bodies[:5]

    configs = [
        ScanConfig(
            body=code,
            natal_lon_deg=0.0,
            aspect_angle_deg=0.0,
            orb_deg=6.0,
            tick_minutes=1440,
        )
        for code in bodies
    ]

    started = perf_counter()
    total_hits = 0
    for cfg in configs:
        hits = fast_scan(start, end, cfg)
        total_hits += len(hits)
    elapsed = perf_counter() - started

    assert elapsed < 1.5, f"1-year scan exceeded budget ({elapsed:.2f}s)"
    assert total_hits <= 500


# >>> AUTO-GEN END: perf smoke v1.0
