"""Endpoints exposing analytical utilities such as midpoint calculations."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Mapping

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from ...analysis.midpoints import compute_midpoints, get_midpoint_settings
from ...chart.config import ChartConfig
from ...chart.natal import ChartLocation, DEFAULT_BODIES, compute_natal_chart
from ...providers.swisseph_adapter import SE_MEAN_NODE, SE_TRUE_NODE
from ...userdata.vault import load_natal

router = APIRouter(prefix="/v1/analysis", tags=["analysis"])


class MidpointItem(BaseModel):
    bodies: tuple[str, str] = Field(
        description="Pair of chart factors used to compute the midpoint.",
        min_length=2,
        max_length=2,
    )
    longitude: float = Field(
        description="Midpoint longitude in degrees (0°–360°).",
        ge=0.0,
        lt=360.0,
    )
    depth: int = Field(
        description="Tree depth where 1 corresponds to direct body midpoints.",
        ge=1,
    )


class MidpointsResponse(BaseModel):
    midpoints: list[MidpointItem]
    source: dict[str, Any] | None = Field(
        default=None, description="Metadata describing the midpoint input source."
    )
    metadata: dict[str, Any] | None = Field(
        default=None, description="Diagnostic metadata about the computation."
    )


def _pair_depth(pair: tuple[str, str]) -> int:
    return max(segment.count("/") for segment in pair) + 1


def _parse_longitudes_payload(value: str | None) -> dict[str, float]:
    if not value:
        return {}
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:  # pragma: no cover - exercised via HTTP
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_LONGITUDES", "message": "longitudes must be JSON"},
        ) from exc
    if not isinstance(payload, Mapping):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_LONGITUDES", "message": "longitudes must be an object"},
        )
    parsed: dict[str, float] = {}
    for raw_name, raw_value in payload.items():
        name = str(raw_name)
        if not name:
            continue
        try:
            parsed[name] = float(raw_value)
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_LONGITUDE_VALUE",
                    "message": f"longitude for '{name}' must be numeric",
                },
            ) from exc
    return parsed


def _chart_config_from_settings(
    include_nodes: bool, base_config: ChartConfig | None = None
) -> tuple[ChartConfig, dict[str, int]]:
    settings = get_midpoint_settings()
    chart_config = base_config or ChartConfig()
    bodies = dict(DEFAULT_BODIES)
    if include_nodes:
        node_variant = chart_config.nodes_variant
        node_code = SE_TRUE_NODE if node_variant == "true" else SE_MEAN_NODE
        label = "True Node" if node_variant == "true" else "Mean Node"
        bodies.setdefault(label, node_code)
        bodies.setdefault("South Node", node_code)
    return chart_config, bodies


def _load_natal_longitudes(natal_id: str, include_nodes: bool) -> dict[str, float]:
    try:
        record = load_natal(natal_id)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "NATAL_NOT_FOUND",
                "message": f"Natal '{natal_id}' was not found.",
            },
        ) from exc
    try:
        moment = datetime.fromisoformat(record.utc.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_NATAL_TIMESTAMP",
                "message": f"Natal '{natal_id}' has an invalid UTC timestamp.",
            },
        ) from exc
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    else:
        moment = moment.astimezone(timezone.utc)

    config, body_map = _chart_config_from_settings(include_nodes, record.chart_config())
    chart = compute_natal_chart(
        moment,
        ChartLocation(latitude=float(record.lat), longitude=float(record.lon)),
        bodies=body_map,
        config=config,
    )
    return {name: pos.longitude for name, pos in chart.positions.items()}


@router.get(
    "/midpoints",
    response_model=MidpointsResponse,
    summary="Compute planetary midpoints.",
    operation_id="getMidpoints",
)
def get_midpoints(
    natal_id: str | None = Query(
        default=None, description="Identifier for a stored natal chart."
    ),
    longitudes: str | None = Query(
        default=None, description="JSON mapping of bodies to longitudes in degrees."
    ),
    include_nodes: bool | None = Query(
        default=None, description="Include lunar nodes when available."
    ),
) -> MidpointsResponse:
    cfg = get_midpoint_settings()
    if not cfg.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "MIDPOINTS_DISABLED",
                "message": "Midpoint analysis is disabled in the current settings.",
            },
        )

    include_nodes_flag = include_nodes if include_nodes is not None else cfg.include_nodes
    payload: dict[str, float]
    source: dict[str, Any] | None = None

    if longitudes:
        payload = _parse_longitudes_payload(longitudes)
        source = {"type": "inline", "count": len(payload)}
    elif natal_id:
        payload = _load_natal_longitudes(natal_id, include_nodes_flag)
        source = {"type": "natal", "natal_id": natal_id, "count": len(payload)}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "MISSING_INPUT",
                "message": "Provide either 'natal_id' or 'longitudes' to compute midpoints.",
            },
        )

    if not payload:
        return MidpointsResponse(midpoints=[], source=source, metadata={"count": 0})

    midpoints = compute_midpoints(payload, include_nodes=include_nodes_flag)
    items = [
        MidpointItem(bodies=pair, longitude=value, depth=_pair_depth(pair))
        for pair, value in midpoints.items()
    ]
    items.sort(key=lambda item: (item.depth, item.bodies[0].casefold(), item.bodies[1].casefold()))
    metadata = {
        "count": len(items),
        "tree": {
            "enabled": cfg.tree.enabled,
            "max_depth": cfg.tree.max_depth,
        },
    }
    return MidpointsResponse(midpoints=items, source=source, metadata=metadata)
