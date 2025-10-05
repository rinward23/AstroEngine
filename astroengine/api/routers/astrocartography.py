"""Astrocartography and relocation endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Iterable, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ...analysis import AstrocartographyResult, MapLine, compute_astrocartography_lines
from ...config import load_settings
from ...ephemeris import SwissEphemerisAdapter
from ...userdata.vault import Natal, load_natal
from ..rate_limit import heavy_endpoint_rate_limiter

router = APIRouter(prefix="/v1/astrocartography", tags=["astrocartography"])


class Feature(BaseModel):
    """GeoJSON Feature representation."""

    type: Literal["Feature"] = "Feature"
    geometry: dict[str, object]
    properties: dict[str, object]


class FeatureCollection(BaseModel):
    """GeoJSON FeatureCollection response."""

    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[Feature]
    metadata: dict[str, object] | None = None


def _parse_csv(value: str | None) -> list[str] | None:
    if value is None:
        return None
    tokens = [token.strip() for chunk in value.split(",") for token in chunk.split()]
    return [token for token in tokens if token]


def _coerce_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _line_to_feature(line: MapLine) -> Feature:
    return Feature(
        geometry={
            "type": "LineString",
            "coordinates": [
                [lon, lat]
                for lon, lat in line.coordinates
            ],
        },
        properties={"body": line.body, "kind": line.kind, **dict(line.metadata)},
    )


def _paran_to_feature(paran: dict[str, object]) -> Feature:
    coordinates = paran.get("coordinates")
    geometry: dict[str, object]
    if isinstance(coordinates, Iterable) and not isinstance(coordinates, (str, bytes)):
        geometry = {
            "type": "MultiPoint",
            "coordinates": [list(point) for point in coordinates],
        }
    else:
        geometry = {"type": "Point", "coordinates": coordinates}
    props = {key: value for key, value in paran.items() if key != "coordinates"}
    return Feature(geometry=geometry, properties=props)


@router.get(
    "",
    response_model=FeatureCollection,
    summary="Render astrocartography linework as GeoJSON.",
    operation_id="astrocartographyLines",
    dependencies=[
        Depends(
            heavy_endpoint_rate_limiter(
                "astrocartography",
                message="Astrocartography map generation is temporarily limited while we process other requests.",
            )
        )
    ],
)
def astrocartography_geojson(
    natal_id: str = Query(..., description="Identifier of the natal chart."),
    bodies: str | None = Query(None, description="Comma-separated list of bodies."),
    line_types: str | None = Query(None, description="Comma-separated line kinds."),
    show_parans: bool | None = Query(None, description="Include paran markers."),
) -> FeatureCollection:
    """Return astrocartography features derived from stored natal data."""

    try:
        natal: Natal = load_natal(natal_id)
    except FileNotFoundError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Natal not found") from exc

    settings = load_settings()
    cfg = settings.astrocartography

    bodies_list = _parse_csv(bodies) or cfg.bodies
    line_list = _parse_csv(line_types) or cfg.line_types
    include_parans = cfg.show_parans if show_parans is None else show_parans

    moment = _coerce_datetime(natal.utc)

    try:
        result: AstrocartographyResult = compute_astrocartography_lines(
            moment,
            bodies=bodies_list,
            adapter=SwissEphemerisAdapter.get_default_adapter(),
            lat_step=cfg.lat_step_deg,
            line_types=line_list,
            simplify_tolerance=cfg.simplify_tolerance_deg,
            show_parans=include_parans,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except (RuntimeError, ModuleNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    features = [_line_to_feature(line) for line in result.lines]
    if include_parans and result.parans:
        features.extend(_paran_to_feature(paran) for paran in result.parans)

    return FeatureCollection(
        features=features,
        metadata={
            "natal_id": natal_id,
            "moment": moment.isoformat().replace("+00:00", "Z"),
            "bodies": bodies_list,
            "line_types": line_list,
            "parans": include_parans,
        },
    )
