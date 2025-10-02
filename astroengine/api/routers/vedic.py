from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ConfigDict, field_validator

from ...chart import ChartLocation
from ...chart.natal import DEFAULT_BODIES
from ...detectors.ingresses import sign_index, ZODIAC_SIGNS
from ...engine.vedic import (
    VimshottariOptions,
    build_context,
    build_vimshottari,
    build_yogini,
    compute_sidereal_chart,
    compute_varga,
    nakshatra_info,
    nakshatra_of,
    position_for,
)
from ...engine.vedic.dasha_yogini import YoginiOptions

router = APIRouter(prefix="/v1/vedic", tags=["vedic"])


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class NatalPayload(BaseModel):
    moment: datetime = Field(alias="datetime")
    model_config = ConfigDict(populate_by_name=True)
    lat: float
    lon: float

    @field_validator("moment", mode="before")
    @classmethod
    def _coerce_datetime(cls, value: Any) -> datetime:
        if isinstance(value, datetime):
            return _normalize_datetime(value)
        if isinstance(value, str):
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return _normalize_datetime(dt)
        raise TypeError("datetime must be ISO-8601 string or datetime")

    @field_validator("lat")
    @classmethod
    def _validate_lat(cls, value: float) -> float:
        if not -90.0 <= value <= 90.0:
            raise ValueError("latitude must be between -90 and 90")
        return value

    @field_validator("lon")
    @classmethod
    def _validate_lon(cls, value: float) -> float:
        if not -180.0 <= value <= 180.0:
            raise ValueError("longitude must be between -180 and 180")
        return value


class ChartRequest(NatalPayload):
    ayanamsa: str = "lahiri"
    house_system: str | None = None
    bodies: list[str] | None = None


class BodyResponse(BaseModel):
    name: str
    longitude: float
    sign: str
    sign_index: int
    nakshatra: str
    nakshatra_index: int
    pada: int
    degree_in_pada: float
    lord: str


class ChartResponse(BaseModel):
    metadata: dict[str, Any]
    bodies: list[BodyResponse]
    ascendant: BodyResponse | None = None


class NakshatraResponse(BaseModel):
    ascendant: BodyResponse | None
    moon: BodyResponse


class VimOptions(BaseModel):
    year_basis: float = 365.25
    anchor: Literal["exact", "midnight"] = "exact"

    @field_validator("year_basis")
    @classmethod
    def _validate_year(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("year_basis must be positive")
        return value


class VimRequest(BaseModel):
    natal: NatalPayload
    ayanamsa: str = "lahiri"
    levels: int = Field(default=3, ge=1, le=3)
    options: VimOptions = Field(default_factory=VimOptions)


class YoginiRequest(BaseModel):
    natal: NatalPayload
    ayanamsa: str = "lahiri"
    levels: int = Field(default=2, ge=1, le=3)
    year_basis: float = 365.25


class DashaPeriodModel(BaseModel):
    system: str
    level: str
    ruler: str
    start: str
    end: str
    metadata: dict[str, Any]


class DashaResponse(BaseModel):
    metadata: dict[str, Any]
    periods: list[DashaPeriodModel]


class VargaRequest(BaseModel):
    natal: NatalPayload
    ayanamsa: str = "lahiri"
    charts: list[
        Literal["D3", "D7", "D9", "D10", "D12", "D16", "D24", "D45", "D60"]
    ]


class VargaResponse(BaseModel):
    metadata: dict[str, Any]
    charts: dict[str, dict[str, dict[str, Any]]]


def _body_payload(name: str, longitude: float) -> BodyResponse:
    sign_idx = sign_index(longitude)
    nak_index = nakshatra_of(longitude)
    info = nakshatra_info(nak_index)
    pos = position_for(longitude)
    return BodyResponse(
        name=name,
        longitude=round(longitude % 360.0, 6),
        sign=ZODIAC_SIGNS[sign_idx],
        sign_index=sign_idx,
        nakshatra=info.name,
        nakshatra_index=info.index,
        pada=pos.pada,
        degree_in_pada=round(pos.degree_in_pada, 6),
        lord=info.lord,
    )


def _chart_from_payload(payload: ChartRequest) -> tuple[Any, dict[str, Any]]:
    location = ChartLocation(latitude=payload.lat, longitude=payload.lon)
    bodies = DEFAULT_BODIES
    if payload.bodies:
        missing = [body for body in payload.bodies if body not in bodies]
        if missing:
            raise HTTPException(status_code=400, detail=f"Unsupported bodies: {missing}")
        bodies = {name: bodies[name] for name in payload.bodies}
    chart = compute_sidereal_chart(
        payload.moment,
        location,
        ayanamsa=payload.ayanamsa,
        house_system=payload.house_system,
        bodies=bodies,
    )
    metadata = {
        "moment": chart.moment.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "location": {"latitude": payload.lat, "longitude": payload.lon},
        "zodiac": chart.zodiac,
        "ayanamsa": chart.ayanamsa,
        "ayanamsa_degrees": chart.ayanamsa_degrees,
        "house_system": chart.metadata.get("house_system") if chart.metadata else payload.house_system,
    }
    return chart, metadata


@router.post("/chart", response_model=ChartResponse)
def vedic_chart(request: ChartRequest) -> ChartResponse:
    chart, metadata = _chart_from_payload(request)
    bodies = [
        _body_payload(name, position.longitude)
        for name, position in chart.positions.items()
    ]
    asc = None
    if chart.houses:
        asc = _body_payload("Ascendant", chart.houses.ascendant)
    return ChartResponse(metadata=metadata, bodies=sorted(bodies, key=lambda b: b.name), ascendant=asc)


@router.post("/nakshatra", response_model=NakshatraResponse)
def vedic_nakshatra(request: ChartRequest) -> NakshatraResponse:
    chart, _ = _chart_from_payload(request)
    moon = chart.positions.get("Moon")
    if moon is None:
        raise HTTPException(status_code=400, detail="Moon position unavailable")
    moon_payload = _body_payload("Moon", moon.longitude)
    asc_payload = None
    if chart.houses:
        asc_payload = _body_payload("Ascendant", chart.houses.ascendant)
    return NakshatraResponse(ascendant=asc_payload, moon=moon_payload)


def _period_payload(period) -> DashaPeriodModel:
    return DashaPeriodModel(
        system=period.system,
        level=period.level,
        ruler=period.ruler,
        start=period.start.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        end=period.end.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        metadata=period.metadata,
    )


@router.post("/dasha/vimshottari", response_model=DashaResponse)
def vedic_vimshottari(request: VimRequest) -> DashaResponse:
    context = build_context(
        request.natal.moment,
        request.natal.lat,
        request.natal.lon,
        ayanamsa=request.ayanamsa,
    )
    options = VimshottariOptions(
        year_basis=request.options.year_basis,
        anchor=request.options.anchor,
    )
    periods = build_vimshottari(context, levels=request.levels, options=options)
    metadata = {
        "ayanamsa": context.chart.ayanamsa,
        "ayanamsa_degrees": context.chart.ayanamsa_degrees,
        "levels": request.levels,
        "year_basis": options.year_basis,
    }
    return DashaResponse(metadata=metadata, periods=[_period_payload(period) for period in periods])


@router.post("/dasha/yogini", response_model=DashaResponse)
def vedic_yogini(request: YoginiRequest) -> DashaResponse:
    context = build_context(
        request.natal.moment,
        request.natal.lat,
        request.natal.lon,
        ayanamsa=request.ayanamsa,
    )
    options = YoginiOptions(year_basis=request.year_basis)
    periods = build_yogini(context, levels=request.levels, options=options)
    metadata = {
        "ayanamsa": context.chart.ayanamsa,
        "ayanamsa_degrees": context.chart.ayanamsa_degrees,
        "levels": request.levels,
        "year_basis": options.year_basis,
    }
    return DashaResponse(metadata=metadata, periods=[_period_payload(period) for period in periods])


@router.post("/varga", response_model=VargaResponse)
def vedic_varga(request: VargaRequest) -> VargaResponse:
    context = build_context(
        request.natal.moment,
        request.natal.lat,
        request.natal.lon,
        ayanamsa=request.ayanamsa,
    )
    charts: dict[str, dict[str, dict[str, Any]]] = {}
    for kind in request.charts:
        charts[kind] = compute_varga(
            context.chart.positions,
            kind,
            ascendant=context.chart.houses.ascendant if context.chart.houses else None,
        )
    metadata = {
        "ayanamsa": context.chart.ayanamsa,
        "ayanamsa_degrees": context.chart.ayanamsa_degrees,
    }
    return VargaResponse(metadata=metadata, charts=charts)
