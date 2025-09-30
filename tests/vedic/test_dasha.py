from datetime import UTC, datetime

import pytest

from astroengine.engine.vedic import (
    VimshottariOptions,
    build_context,
    build_vimshottari,
    build_yogini,
)
from astroengine.engine.vedic.dasha_vimshottari import ORDER, TOTAL_YEARS
from astroengine.engine.vedic.dasha_yogini import TOTAL_YEARS as YOGINI_TOTAL


NATAL_MOMENT = datetime(1984, 10, 17, 4, 30, tzinfo=UTC)
LAT = 40.7128
LON = -74.0060


def test_vimshottari_maha_cycle_totals():
    ctx = build_context(NATAL_MOMENT, LAT, LON)
    periods = build_vimshottari(ctx, levels=3, options=VimshottariOptions())
    maha = [p for p in periods if p.level == "maha"]
    assert maha[0].ruler == "Jupiter"
    assert maha[0].start == ctx.chart.moment
    total_years = sum(p.metadata["span_years"] for p in maha)
    assert pytest.approx(total_years, rel=1e-6) == TOTAL_YEARS
    for idx in range(len(maha) - 1):
        assert maha[idx].end == maha[idx + 1].start
    balance = maha[0].metadata.get("balance_years")
    assert balance is not None and 0 < balance < dict(ORDER)["Jupiter"]


def test_yogini_cycle_totals():
    ctx = build_context(NATAL_MOMENT, LAT, LON)
    periods = build_yogini(ctx, levels=2)
    maha = [p for p in periods if p.level == "maha"]
    assert maha[0].ruler == "Siddha"
    total_years = sum(p.metadata["span_years"] for p in maha)
    assert pytest.approx(total_years, rel=1e-6) == YOGINI_TOTAL
    for idx in range(len(maha) - 1):
        assert maha[idx].end == maha[idx + 1].start
