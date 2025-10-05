"""FastAPI router for the transit ↔ natal overlay visualisation."""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException
from fastapi.responses import ORJSONResponse, Response

from ...chart.natal import ChartLocation
from ...ux.maps.transit_overlay import (
    AspectHit,
    OverlayBodyState,
    OverlayFrame,
    OverlayOptions,
    OverlayRequest,
    TransitOverlayResult,
    compute_overlay_frames,
    compute_transit_aspects,
    render_overlay_svg,
)
from ..schemas_transit_overlay import (
    OverlayBodyPositionModel,
    OverlayFrameModel,
    TransitAspectModel,
    TransitAspectRequest,
    TransitAspectResponse,
    TransitOverlayExportRequest,
    TransitOverlayPositionRequest,
    TransitOverlayPositionResponse,
)

router = APIRouter(
    prefix="/v1/transit-overlay",
    tags=["transit-overlay"],
    default_response_class=ORJSONResponse,
)


@router.post("/positions", response_model=TransitOverlayPositionResponse)
def positions(payload: TransitOverlayPositionRequest) -> TransitOverlayPositionResponse:
    if not payload.bodies:
        raise HTTPException(status_code=400, detail="At least one body must be requested")
    options_mapping = payload.options.model_dump(exclude_none=True) if payload.options else None
    request = OverlayRequest(
        birth_dt=payload.birth_dt_utc,
        birth_location=ChartLocation(
            latitude=payload.birth_location.lat,
            longitude=payload.birth_location.lon,
        ),
        transit_dt=payload.transit_dt_utc,
        bodies=payload.bodies,
        options=options_mapping,
    )
    try:
        result = compute_overlay_frames(request)
    except ModuleNotFoundError as exc:  # Swiss Ephemeris not available
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _response_from_result(result)


@router.post("/aspects", response_model=TransitAspectResponse)
def aspects(payload: TransitAspectRequest) -> TransitAspectResponse:
    natal = {name: _state_from_model(model) for name, model in payload.natal.geocentric.items()}
    transit = {name: _state_from_model(model) for name, model in payload.transit.geocentric.items()}
    overrides = {name: float(value) for name, value in (payload.orb_overrides or {}).items()}
    hits = compute_transit_aspects(
        natal,
        transit,
        conj_override=payload.conj_override,
        opp_override=payload.opp_override,
        per_body_overrides=overrides,
    )
    return TransitAspectResponse(aspects=[TransitAspectModel(**asdict(hit)) for hit in hits])


@router.post("/export", response_class=Response)
def export_svg(payload: TransitOverlayExportRequest) -> Response:
    result = _result_from_response(payload.payload)
    aspect_hits = [
        AspectHit(
            body=model.body,
            kind=model.kind,
            separation_deg=model.separation_deg,
            orb_abs_deg=model.orb_abs_deg,
        )
        for model in (payload.aspects or [])
    ]
    width = payload.width or 900
    height = payload.height or 900
    theme = payload.theme or "light"
    svg = render_overlay_svg(result, aspects=aspect_hits, width=width, height=height, theme=theme)
    return Response(content=svg, media_type="image/svg+xml")


def _response_from_result(result: TransitOverlayResult) -> TransitOverlayPositionResponse:
    return TransitOverlayPositionResponse(
        natal=OverlayFrameModel(**result.natal.to_dict()),
        transit=OverlayFrameModel(**result.transit.to_dict()),
        options=result.options.to_dict(),
    )


def _state_from_model(model: OverlayBodyPositionModel) -> OverlayBodyState:
    return OverlayBodyState(
        id=model.id,
        lon_deg=model.lon_deg,
        lat_deg=model.lat_deg,
        radius_au=model.radius_au,
        speed_lon_deg_per_day=model.speed_lon_deg_per_day,
        speed_lat_deg_per_day=model.speed_lat_deg_per_day,
        speed_radius_au_per_day=model.speed_radius_au_per_day,
        retrograde=model.retrograde,
        frame=model.frame,
        metadata=dict(model.metadata or {}),
    )


def _frame_from_model(model: OverlayFrameModel) -> OverlayFrame:
    return OverlayFrame(
        timestamp=model.timestamp,
        heliocentric={name: _state_from_model(body) for name, body in model.heliocentric.items()},
        geocentric={name: _state_from_model(body) for name, body in model.geocentric.items()},
        metadata=dict(model.metadata or {}),
    )


def _result_from_response(model: TransitOverlayPositionResponse) -> TransitOverlayResult:
    options = OverlayOptions.from_mapping(model.options)
    natal = _frame_from_model(model.natal)
    transit = _frame_from_model(model.transit)
    return TransitOverlayResult(natal=natal, transit=transit, options=options)
