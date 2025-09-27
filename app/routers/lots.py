from __future__ import annotations

from typing import Dict, List

from fastapi import APIRouter, HTTPException

from app.schemas.lots import (
    LotDefIn,
    LotDefOut,
    LotsCatalogResponse,
    LotsComputeRequest,
    LotsComputeResponse,
)
from core.lots_plus.catalog import (
    REGISTRY,
    LotDef,
    Sect,
    compute_lots,
    register_lot,
)

router = APIRouter(prefix="", tags=["Plus"])


@router.get("/lots/catalog", response_model=LotsCatalogResponse, summary="List Arabic Lots catalog")
def lots_catalog():
    items: List[LotDefOut] = []
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
    return LotsCatalogResponse(lots=items, meta={"count": len(items)})


def _persist_custom_lots(custom_lots: List[LotDefIn]) -> Dict[str, LotDef]:
    """Register inline lots without committing them to the runtime registry."""

    temp_registry: Dict[str, LotDef] = {}
    for c in custom_lots:
        if not c.name or not c.day or not c.night:
            raise HTTPException(
                status_code=400,
                detail="custom_lots entries require name/day/night",
            )
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
    temp_defs: Dict[str, LotDef] = {}
    custom_names: List[str] = []

    if req.custom_lots:
        temp_defs = _persist_custom_lots(req.custom_lots)
        custom_names = [c.name for c in req.custom_lots]

    names = list(dict.fromkeys([*(req.lots or []), *custom_names]))
    if not names:
        raise HTTPException(status_code=400, detail="No lots requested")

    to_cleanup: List[str] = []
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

