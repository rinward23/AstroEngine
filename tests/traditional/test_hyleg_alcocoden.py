from __future__ import annotations

from datetime import UTC, datetime

from astroengine.chart.natal import ChartLocation, compute_natal_chart
from astroengine.engine.traditional import (
    build_chart_context,
    find_alcocoden,
    find_hyleg,
    load_traditional_profiles,
)
from astroengine.engine.traditional.sect import sect_info
from core.lots_plus.catalog import Sect as LotSect
from core.lots_plus.catalog import compute_lots


def _context(include_fortune: bool = False):
    moment = datetime(1984, 10, 26, 18, 15, tzinfo=UTC)
    location = ChartLocation(latitude=34.0522, longitude=-118.2437)
    chart = compute_natal_chart(moment, location)
    sect = sect_info(moment, location)
    positions = {name: pos.longitude for name, pos in chart.positions.items()}
    positions["Asc"] = chart.houses.ascendant
    lots = compute_lots(["Fortune", "Spirit"], positions, LotSect.DAY if sect.is_day else LotSect.NIGHT)
    ctx = build_chart_context(chart=chart, sect=sect, lots=lots)
    profile = load_traditional_profiles()["life"]["profile"]
    if include_fortune:
        profile = type(profile)(
            house_candidates=profile.house_candidates,
            include_fortune=True,
            dignity_weights=profile.dignity_weights,
            lifespan_years=profile.lifespan_years,
            bounds_scheme=profile.bounds_scheme,
            notes=profile.notes,
        )
    return ctx, profile


def test_find_hyleg_prefers_sect_luminary() -> None:
    ctx, profile = _context()
    result = find_hyleg(ctx, profile)
    assert result.body in {"Sun", "Moon", "Asc"}
    assert result.score > 0
    assert result.notes


def test_find_alcocoden_from_hyleg() -> None:
    ctx, profile = _context(include_fortune=True)
    hyleg = find_hyleg(ctx, profile)
    alcocoden = find_alcocoden(ctx, hyleg, profile)
    assert alcocoden.body
    if alcocoden.indicative_years is not None:
        assert alcocoden.indicative_years.minor_years > 0
    assert alcocoden.confidence > 0.0
