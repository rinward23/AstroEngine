"""FastAPI application exposing AstroEngine services."""

from __future__ import annotations

try:  # pragma: no cover - optional dependency
    from fastapi import FastAPI
except Exception:  # pragma: no cover
    app = None  # type: ignore[assignment]
else:
    app = FastAPI(title="AstroEngine API")

if app:
    from .api.routers.plus import router as plus_router
    from .api.routers.interpret import router as interpret_router
    from .api.routers.synastry import router as syn_router

    app.include_router(plus_router)
    app.include_router(interpret_router)
    app.include_router(syn_router, prefix="/v1/synastry", tags=["synastry"])

# >>> AUTO-GEN BEGIN: api-natals v1.0
if app:
    from fastapi import HTTPException

    from .api.routers.scan import router as scan_router
    from .userdata.vault import Natal, list_natals, load_natal, save_natal

    app.include_router(scan_router, prefix="/v1/scan", tags=["scan"])

    @app.get("/natals")
    def api_natals_list():
        return list_natals()

    @app.get("/natals/{natal_id}")
    def api_natals_get(natal_id: str):
        try:
            return load_natal(natal_id).__dict__
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="natal not found") from None

    @app.post("/natals/{natal_id}")
    def api_natals_put(natal_id: str, payload: dict):
        try:
            n = Natal(
                natal_id=natal_id,
                name=payload.get("name"),
                utc=payload["utc"],
                lat=float(payload["lat"]),
                lon=float(payload["lon"]),
                tz=payload.get("tz"),
                place=payload.get("place"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=400, detail="invalid natal payload"
            ) from exc
        save_natal(n)
        return {"ok": True}


# >>> AUTO-GEN END: api-natals v1.0
