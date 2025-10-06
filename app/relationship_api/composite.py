"""Composite and Davison endpoint orchestration."""

from __future__ import annotations

from core.relationship_plus.composite import (
    Geo,
    composite_positions,
    davison_midpoints,
    davison_positions,
)

from .errors import ServiceError
from .models import (
    ChartPositions,
    CompositeRequest,
    CompositeResponse,
    DavisonRequest,
    DavisonResponse,
    EclipticPos,
)
from .providers import make_position_provider
from .synastry import chart_longitudes


def _positions_to_chart(mapping: dict[str, float]) -> ChartPositions:
    payload = {name: EclipticPos(lon=float(lon)) for name, lon in mapping.items()}
    return ChartPositions.model_validate(payload)


def handle_composite(request: CompositeRequest) -> CompositeResponse:
    pos_a = chart_longitudes(request.positionsA)
    pos_b = chart_longitudes(request.positionsB)
    bodies = request.bodies
    result = composite_positions(pos_a, pos_b, bodies=bodies)
    if not result:
        raise ServiceError("MISSING_BODY", "No overlapping bodies for composite", details={"bodies": bodies})
    return CompositeResponse(positions=_positions_to_chart(result))


def handle_davison(request: DavisonRequest) -> DavisonResponse:
    bodies = request.bodies
    if not bodies:
        raise ServiceError("BAD_INPUT", "At least one body must be specified", status_code=400)
    provider = make_position_provider(request.eph, request.node_policy, bodies)
    geo_a = Geo(lat_deg=request.birthA.lat, lon_deg_east=request.birthA.lon)
    geo_b = Geo(lat_deg=request.birthB.lat, lon_deg_east=request.birthB.lon)
    positions = davison_positions(provider, request.birthA.when, geo_a, request.birthB.when, geo_b, bodies=bodies)
    missing = [body for body in bodies if body not in positions]
    if missing:
        raise ServiceError("MISSING_BODY", "Ephemeris missing requested bodies", details={"missing": missing})
    mid_dt, mid_lat, mid_lon = davison_midpoints(request.birthA.when, geo_a, request.birthB.when, geo_b)
    chart = _positions_to_chart(positions)
    return DavisonResponse(mid_when=mid_dt, mid_lat=mid_lat, mid_lon=mid_lon, positions=chart)


__all__ = ["handle_composite", "handle_davison"]
