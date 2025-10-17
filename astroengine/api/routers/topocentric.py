"""FastAPI routes exposing observational geometry utilities."""

from __future__ import annotations

import base64
from datetime import UTC, datetime
from functools import lru_cache

from fastapi import APIRouter, HTTPException

from astroengine.ephemeris.swe import has_swe, swe

from ...engine.observational import (
    EventOptions,
    HeliacalProfile,
    MetConditions,
    VisibilityConstraints,
    VisibilityWindow,
    heliacal_candidates,
    horizontal_from_equatorial,
    render_altaz_diagram,
    rise_set_times,
    topocentric_ecliptic,
    topocentric_equatorial,
    transit_time,
    visibility_windows,
)
from ...ephemeris import EphemerisAdapter, EphemerisConfig, ObserverLocation
from ..schemas_observational import (
    DiagramRequest,
    DiagramResponse,
    EventsRequest,
    EventsResponse,
    HeliacalRequest,
    HeliacalResponse,
    MetModel,
    ObserverModel,
    TopocentricPositionRequest,
    TopocentricPositionResponse,
    VisibilityConstraintsModel,
    VisibilityRequest,
    VisibilityResponse,
    VisibilityWindowModel,
)

router = APIRouter(prefix="/topocentric", tags=["topocentric"])

_UNAVAILABLE_DETAIL = "Swiss Ephemeris is not available"


def _ensure_swe_available() -> None:
    if not has_swe():
        raise HTTPException(status_code=503, detail=_UNAVAILABLE_DETAIL)


@lru_cache(maxsize=1)
def _adapter_factory() -> EphemerisAdapter:
    return EphemerisAdapter(EphemerisConfig())


def _get_adapter() -> EphemerisAdapter:
    _ensure_swe_available()
    return _adapter_factory()


@lru_cache(maxsize=1)
def _body_codes() -> tuple[int, int]:
    swe_module = swe()
    return int(getattr(swe_module, "SUN", 0)), int(getattr(swe_module, "MOON", 1))


def _get_body_codes() -> tuple[int, int]:
    _ensure_swe_available()
    return _body_codes()


def _observer_from_model(model: ObserverModel) -> ObserverLocation:
    return ObserverLocation(
        latitude_deg=model.latitude_deg,
        longitude_deg=model.longitude_deg,
        elevation_m=model.elevation_m,
    )


def _met_from_model(model: MetModel | None) -> MetConditions:
    if model is None:
        return MetConditions()
    return MetConditions(
        temperature_c=model.temperature_c,
        pressure_hpa=model.pressure_hpa,
    )


def _to_iso(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.astimezone(UTC)


@router.post("/positions", response_model=TopocentricPositionResponse)
def compute_positions(payload: TopocentricPositionRequest) -> TopocentricPositionResponse:
    observer = _observer_from_model(payload.observer)
    adapter = _get_adapter()
    topo_equ = topocentric_equatorial(adapter, payload.body, payload.moment, observer)
    topo_ecl = topocentric_ecliptic(adapter, payload.body, payload.moment, observer)
    horiz = horizontal_from_equatorial(
        topo_equ.right_ascension_deg,
        topo_equ.declination_deg,
        payload.moment,
        observer,
        refraction=payload.refraction,
        met=_met_from_model(payload.met),
        horizon_dip_deg=payload.horizon_dip_deg,
    )
    return TopocentricPositionResponse(
        right_ascension=topo_equ.right_ascension_deg,
        declination=topo_equ.declination_deg,
        distance_au=topo_equ.distance_au,
        ecliptic_longitude=topo_ecl.longitude_deg,
        ecliptic_latitude=topo_ecl.latitude_deg,
        altitude=horiz.altitude_deg,
        azimuth=horiz.azimuth_deg,
        refraction_applied=payload.refraction,
    )


@router.post("/events", response_model=EventsResponse)
def compute_events(payload: EventsRequest) -> EventsResponse:
    observer = _observer_from_model(payload.observer)
    adapter = _get_adapter()
    options = EventOptions(
        refraction=payload.refraction,
        met=_met_from_model(payload.met),
        horizon_dip_deg=payload.horizon_dip_deg,
    )
    rise, set_ = rise_set_times(
        adapter,
        payload.body,
        payload.date,
        observer,
        h0_deg=payload.h0_deg,
        options=options,
    )
    transit = transit_time(adapter, payload.body, payload.date, observer)
    return EventsResponse(rise=_to_iso(rise), set=_to_iso(set_), transit=_to_iso(transit))


@router.post("/visibility", response_model=VisibilityResponse)
def compute_visibility(payload: VisibilityRequest) -> VisibilityResponse:
    observer = _observer_from_model(payload.observer)
    adapter = _get_adapter()
    constraints = _constraints_from_model(payload.constraints)
    windows = visibility_windows(
        adapter,
        payload.body,
        payload.start,
        payload.end,
        observer,
        constraints,
    )
    return VisibilityResponse(windows=[_window_to_model(w) for w in windows])


@router.post("/heliacal", response_model=HeliacalResponse)
def compute_heliacal(payload: HeliacalRequest) -> HeliacalResponse:
    observer = _observer_from_model(payload.observer)
    adapter = _get_adapter()
    profile = HeliacalProfile(
        mode=payload.profile.mode,
        min_object_altitude_deg=payload.profile.min_object_altitude_deg,
        sun_altitude_max_deg=payload.profile.sun_altitude_max_deg,
        sun_separation_min_deg=payload.profile.sun_separation_min_deg,
        max_airmass=payload.profile.max_airmass,
        refraction=payload.profile.refraction,
        search_window_hours=payload.profile.search_window_hours,
    )
    instants = heliacal_candidates(
        adapter,
        payload.body,
        (payload.start, payload.end),
        observer,
        profile,
    )
    instants = [_to_iso(dt) for dt in instants if dt is not None]
    return HeliacalResponse(instants=[dt for dt in instants if dt is not None])


@router.post("/altaz/diagram", response_model=DiagramResponse)
def generate_diagram(payload: DiagramRequest) -> DiagramResponse:
    observer = _observer_from_model(payload.observer)
    adapter = _get_adapter()
    diagram = render_altaz_diagram(
        adapter,
        payload.body,
        payload.start,
        payload.end,
        observer,
        refraction=payload.refraction,
        met=_met_from_model(payload.met),
        horizon_dip_deg=payload.horizon_dip_deg,
        step_seconds=payload.step_seconds,
        include_png=payload.include_png,
    )
    png_b64 = base64.b64encode(diagram.png).decode("ascii") if diagram.png else None
    return DiagramResponse(svg=diagram.svg, png_base64=png_b64, metadata=diagram.metadata)


def _constraints_from_model(model: VisibilityConstraintsModel) -> VisibilityConstraints:
    met = _met_from_model(model.met)
    sun_body = model.sun_body
    moon_body = model.moon_body
    if sun_body is None or moon_body is None:
        default_sun, default_moon = _get_body_codes()
        if sun_body is None:
            sun_body = default_sun
        if moon_body is None:
            moon_body = default_moon

    return VisibilityConstraints(
        min_altitude_deg=model.min_altitude_deg,
        sun_altitude_max_deg=model.sun_altitude_max_deg,
        sun_separation_min_deg=model.sun_separation_min_deg,
        moon_altitude_max_deg=model.moon_altitude_max_deg,
        refraction=model.refraction,
        met=met,
        horizon_dip_deg=model.horizon_dip_deg,
        step_seconds=model.step_seconds,
        sun_body=sun_body,
        moon_body=moon_body,
    )


def _window_to_model(window: VisibilityWindow | VisibilityWindowModel) -> VisibilityWindowModel:
    if isinstance(window, VisibilityWindowModel):
        return window
    return VisibilityWindowModel(
        start=window.start,
        end=window.end,
        duration_seconds=window.duration_seconds,
        max_altitude_deg=window.max_altitude_deg,
        max_altitude_time=window.max_altitude_time,
        min_sun_separation_deg=window.min_sun_separation_deg,
        max_sun_separation_deg=window.max_sun_separation_deg,
        score=window.score,
        details=window.details,
    )


__all__ = ["router"]
