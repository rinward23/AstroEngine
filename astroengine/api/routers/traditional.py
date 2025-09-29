"""FastAPI router exposing traditional timing engines."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException

from ...chart.natal import ChartLocation, NatalChart, compute_natal_chart
from core.lots_plus.catalog import Sect as LotSect
from core.lots_plus.catalog import compute_lots
from ...engine.traditional import (
    Interval,
    apply_loosing_of_bond,
    build_chart_context,
    find_alcocoden,
    find_hyleg,
    flag_peaks_fortune,
    load_traditional_profiles,
    profection_year_segments,
    sect_info,
    zr_periods,
)
from ...engine.traditional.models import LifeProfile
from ...engine.traditional.zr import SIGN_ORDER
from ..schemas_traditional import (
    AlcocodenOut,
    LifeMetadata,
    LifeRequest,
    LifeResponse,
    ProfectionSegmentOut,
    ProfectionsRequest,
    ProfectionsResponse,
    SectRequest,
    SectResponse,
    TraditionalChartInput,
    ZodiacalPeriodOut,
    ZodiacalReleasingRequest,
    ZodiacalReleasingResponse,
)

router = APIRouter(prefix="/v1/traditional", tags=["traditional"])


def _chart_location(data: TraditionalChartInput) -> ChartLocation:
    return ChartLocation(latitude=float(data.latitude), longitude=float(data.longitude))


def _lot_sect(sect: bool) -> str:
    return LotSect.DAY if sect else LotSect.NIGHT


def _lot_positions(chart: NatalChart) -> dict[str, float]:
    positions = {name: pos.longitude for name, pos in chart.positions.items()}
    positions["Asc"] = chart.houses.ascendant
    return positions


def _fortune_sign(lot_degree: float | None) -> str | None:
    if lot_degree is None:
        return None
    index = int(lot_degree % 360.0 // 30.0)
    return SIGN_ORDER[index]


def _build_context(data: TraditionalChartInput) -> ChartCtx:
    moment = data.moment
    if moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None:
        raise ValueError("Moment must be timezone-aware")
    location = _chart_location(data)
    chart = compute_natal_chart(moment, location)
    sect = sect_info(moment, location)
    lots = compute_lots(["Fortune", "Spirit"], _lot_positions(chart), _lot_sect(sect.is_day))
    return build_chart_context(chart=chart, sect=sect, lots=lots, house_system=data.house_system or "whole_sign")


def _segment_to_response(segment: Any) -> ProfectionSegmentOut:
    return ProfectionSegmentOut(
        start=segment.start.astimezone(UTC),
        end=segment.end.astimezone(UTC),
        house=segment.house,
        sign=segment.sign,
        year_lord=segment.year_lord,
        co_rulers=dict(segment.co_rulers),
        notes=list(segment.notes),
    )


@router.post("/profections", response_model=ProfectionsResponse)
def api_profections(request: ProfectionsRequest) -> ProfectionsResponse:
    try:
        ctx = _build_context(request.natal)
        interval = Interval(start=request.start.astimezone(UTC), end=request.end.astimezone(UTC))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    segments = profection_year_segments(ctx, interval, mode=request.mode)
    payload = [_segment_to_response(seg) for seg in segments]
    return ProfectionsResponse(
        segments=payload,
        meta={
            "count": len(payload),
            "mode": request.mode,
            "house_system": ctx.house_system,
        },
    )


def _period_to_response(period: Any) -> ZodiacalPeriodOut:
    metadata = dict(period.metadata)
    return ZodiacalPeriodOut(
        level=period.level,
        start=period.start.astimezone(UTC),
        end=period.end.astimezone(UTC),
        sign=period.sign,
        ruler=period.ruler,
        lb=bool(period.lb),
        lb_from=period.lb_from,
        lb_to=period.lb_to,
        metadata=metadata or None,
    )


@router.post("/zr", response_model=ZodiacalReleasingResponse)
def api_zodiacal_releasing(request: ZodiacalReleasingRequest) -> ZodiacalReleasingResponse:
    try:
        ctx = _build_context(request.natal)
        timeline = zr_periods(
            request.lot_sign,
            request.start.astimezone(UTC),
            request.end.astimezone(UTC),
            levels=request.levels,
            source=request.source,
        )
        timeline = apply_loosing_of_bond(timeline)
        fortune_sign = _fortune_sign(ctx.lot("Fortune"))
        if request.include_peaks and fortune_sign:
            flag_peaks_fortune(timeline, fortune_sign)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    levels_payload: dict[str, list[ZodiacalPeriodOut]] = {}
    for level, periods in timeline.levels.items():
        levels_payload[str(level)] = [_period_to_response(period) for period in periods]
    return ZodiacalReleasingResponse(
        levels=levels_payload,
        lot=timeline.lot,
        source=request.source,
        meta={"levels": request.levels},
    )


@router.post("/sect", response_model=SectResponse)
def api_sect(request: SectRequest) -> SectResponse:
    moment = request.moment
    if moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None:
        raise HTTPException(status_code=400, detail="moment must be timezone-aware")
    info = sect_info(
        moment,
        ChartLocation(latitude=request.latitude, longitude=request.longitude),
    )
    return SectResponse(
        is_day=info.is_day,
        luminary_of_sect=info.luminary_of_sect,
        malefic_of_sect=info.malefic_of_sect,
        benefic_of_sect=info.benefic_of_sect,
        sun_altitude_deg=info.sun_altitude_deg,
    )


def _life_metadata(result: Any) -> LifeMetadata:
    trace = []
    for entry in result.trace:
        if isinstance(entry, tuple) and len(entry) == 2:
            trace.append({"factor": entry[0], "score": entry[1]})
        else:
            trace.append(entry)
    return LifeMetadata(
        body=result.body,
        degree=float(result.degree),
        sign=result.sign,
        house=int(result.house),
        score=float(result.score) if getattr(result, "score", None) is not None else None,
        notes=list(result.notes),
        trace=trace,
    )


def _alcocoden_metadata(result: Any) -> AlcocodenOut:
    years = None
    if result.indicative_years is not None:
        years = {
            "minor": result.indicative_years.minor_years,
            "mean": result.indicative_years.mean_years,
            "major": result.indicative_years.major_years,
        }
    return AlcocodenOut(
        body=result.body,
        method=result.method,
        indicative_years=years,
        confidence=float(result.confidence),
        notes=list(result.notes),
        trace=list(result.trace),
    )


@router.post("/life", response_model=LifeResponse)
def api_life(request: LifeRequest) -> LifeResponse:
    profiles = load_traditional_profiles()
    profile: LifeProfile = profiles["life"]["profile"]
    profile = LifeProfile(
        house_candidates=profile.house_candidates,
        include_fortune=request.include_fortune,
        dignity_weights=profile.dignity_weights,
        lifespan_years=profile.lifespan_years,
        bounds_scheme=profile.bounds_scheme,
        notes=profile.notes,
    )
    try:
        ctx = _build_context(request.natal)
        hyleg = find_hyleg(ctx, profile)
        alcocoden = find_alcocoden(ctx, hyleg, profile)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return LifeResponse(
        hyleg=_life_metadata(hyleg),
        alcocoden=_alcocoden_metadata(alcocoden),
        meta={"include_fortune": request.include_fortune},
    )
