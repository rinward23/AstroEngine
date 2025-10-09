from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Response

from app.schemas.lots import (
    LotDefIn,
    LotDefOut,
    LotsCatalogResponse,
    LotsComputeRequest,
    LotsComputeResponse,
)
from astroengine.web.responses import conditional_json_response
from core.lots_plus.catalog import (
    REGISTRY,
    LotDef,
    Sect,
    compute_lots,
    register_lot,
)
from core.lots_plus.parser import FormulaSyntaxError, parse_formula

router = APIRouter(prefix="", tags=["Plus"])


@router.get("/lots/catalog", response_model=LotsCatalogResponse, summary="List Arabic Lots catalog")
def lots_catalog(
    if_none_match: str | None = Header(default=None, alias="If-None-Match")
) -> Response:
    items: list[LotDefOut] = []
    for name, lot in REGISTRY.items():
        items.append(
            LotDefOut(
                name=name,
                day=lot.day,
                night=lot.night,
                description=lot.description or "",
            )
        )
    items.sort(key=lambda x: x.name.lower())
    payload = LotsCatalogResponse(lots=items, meta={"count": len(items)})
    return conditional_json_response(
        payload.model_dump(mode="json"),
        if_none_match=if_none_match,
        max_age=86400,
    )


def _persist_custom_lots(custom_lots: list[LotDefIn]) -> dict[str, LotDef]:
    """Register inline lots without committing them to the runtime registry."""

    temp_registry: dict[str, LotDef] = {}
    for c in custom_lots:
        if not c.name or not c.day or not c.night:
            raise HTTPException(
                status_code=400,
                detail="custom_lots entries require name/day/night",
            )
        try:
            parse_formula(c.day)
            parse_formula(c.night)
        except FormulaSyntaxError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        definition = LotDef(
            name=c.name,
            day=c.day,
            night=c.night,
            description=c.description or "",
        )
        if c.register:
            try:
                register_lot(definition, overwrite=False)
            except KeyError as exc:  # duplicate names
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        else:
            temp_registry[definition.name] = definition
    return temp_registry


@router.post(
    "/lots/compute",
    response_model=LotsComputeResponse,
    summary="Compute Arabic Lots (built-in + optional custom)",
    description=(
        "Evaluates requested Lots with sect-aware formulas. Optionally include inline "
        "custom lots; set register=true to add to the runtime catalog."
    ),
)
def lots_compute(req: LotsComputeRequest):
    temp_defs: dict[str, LotDef] = {}
    custom_names: list[str] = []

    if req.custom_lots:
        temp_defs = _persist_custom_lots(req.custom_lots)
        custom_names = [c.name for c in req.custom_lots]

    names = list(dict.fromkeys([*(req.lots or []), *custom_names]))
    if not names:
        raise HTTPException(status_code=400, detail="No lots requested")

    to_cleanup: list[str] = []
    for name, definition in temp_defs.items():
        if name in REGISTRY:
            raise HTTPException(status_code=400, detail=f"Lot already exists: {name}")
        REGISTRY[name] = definition
        to_cleanup.append(name)

    try:
        sect = Sect.DAY if req.sect == "day" else Sect.NIGHT
        vals = compute_lots(names, req.positions, sect)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        for name in to_cleanup:
            REGISTRY.pop(name, None)

    return LotsComputeResponse(positions=vals, meta={"sect": req.sect, "count": len(vals)})
