from __future__ import annotations

from datetime import UTC, datetime

from astroengine.chart.natal import ChartLocation, compute_natal_chart
from astroengine.engine.traditional import (
    Interval,
    build_chart_context,
    current_profection,
    profection_year_segments,
)
from astroengine.engine.traditional.profections import SIGN_SEQUENCE
from astroengine.engine.traditional.sect import sect_info
from core.lots_plus.catalog import Sect as LotSect
from core.lots_plus.catalog import compute_lots


def _context() -> tuple:
    moment = datetime(1990, 5, 15, 12, 0, tzinfo=UTC)
    location = ChartLocation(latitude=51.5074, longitude=-0.1278)
    chart = compute_natal_chart(moment, location)
    sect = sect_info(moment, location)
    positions = {name: pos.longitude for name, pos in chart.positions.items()}
    positions["Asc"] = chart.houses.ascendant
    lots = compute_lots(["Fortune", "Spirit"], positions, LotSect.DAY if sect.is_day else LotSect.NIGHT)
    ctx = build_chart_context(chart=chart, sect=sect, lots=lots)
    return ctx, moment


def test_profection_year_progression() -> None:
    ctx, _ = _context()
    start = datetime(2020, 5, 15, 12, 0, tzinfo=UTC)
    end = datetime(2022, 5, 15, 12, 0, tzinfo=UTC)
    interval = Interval(start=start, end=end)
    segments = profection_year_segments(ctx, interval)
    years = [seg for seg in segments if seg.notes and seg.notes[0].startswith("age=")]
    assert years, "expected annual profection segments"
    first_year = years[0]
    assert first_year.house == 7
    asc_index = int(ctx.natal.houses.ascendant % 360.0 // 30.0)
    expected_sign = SIGN_SEQUENCE[(asc_index + 30) % 12]
    assert first_year.sign == expected_sign
    months = [seg for seg in segments if seg.notes and seg.notes[0].startswith("month=")]
    month1 = next(seg for seg in months if seg.notes[0] == "month=1")
    month6 = next(seg for seg in months if seg.notes[0] == "month=6")
    assert month1.house == first_year.house
    assert month6.house == ((first_year.house + 5 - 1) % 12) + 1


def test_medieval_month_mode_differs() -> None:
    ctx, _ = _context()
    start = datetime(2020, 5, 15, 12, 0, tzinfo=UTC)
    end = datetime(2021, 5, 15, 12, 0, tzinfo=UTC)
    interval = Interval(start=start, end=end)
    hellenistic = profection_year_segments(ctx, interval, mode="hellenistic")
    medieval = profection_year_segments(ctx, interval, mode="medieval")
    hell_months = {seg.notes[0]: seg.house for seg in hellenistic if seg.notes and seg.notes[0].startswith("month=")}
    med_months = {seg.notes[0]: seg.house for seg in medieval if seg.notes and seg.notes[0].startswith("month=")}
    assert hell_months and med_months
    assert hell_months != med_months


def test_current_profection_matches_timeline() -> None:
    ctx, _ = _context()
    moment = datetime(2021, 1, 1, 0, 0, tzinfo=UTC)
    state = current_profection(moment, ctx)
    assert state.year_house == 7
    year_start = datetime(2020, 5, 15, 12, 0, tzinfo=UTC)
    year_end = datetime(2021, 5, 15, 12, 0, tzinfo=UTC)
    full_interval = Interval(start=year_start, end=year_end)
    segments = profection_year_segments(ctx, full_interval)
    month_segment = next(
        seg for seg in segments if seg.notes and seg.notes[0].startswith("month=") and seg.start <= moment < seg.end
    )
    assert state.month_house == month_segment.house
