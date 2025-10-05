"""FastAPI application exposing AstroEngine services."""

from __future__ import annotations

try:  # pragma: no cover - optional dependency
    from fastapi import FastAPI
    from fastapi.responses import ORJSONResponse
except Exception:  # pragma: no cover
    app = None  # type: ignore[assignment]
else:
    app = FastAPI(
        title="AstroEngine API",
        version="1.0",
        default_response_class=ORJSONResponse,
        openapi_tags=[
            {"name": "system", "description": "Service level operations."},
            {"name": "interpret", "description": "Relationship interpretation services."},
            {"name": "natals", "description": "Stored natal chart management."},
            {"name": "scan", "description": "Transit and progression scanning."},
            {"name": "synastry", "description": "Synastry chart operations."},
            {"name": "analysis", "description": "Catalog and fixed-star lookups."},
        ],
    )

if app:
    from fastapi.middleware.gzip import GZipMiddleware

    from .api.errors import install_error_handlers
    from .api.routers.analysis import router as analysis_router
    from .api.routers.interpret import router as interpret_router
    from .api.routers.natals import router as natals_router
    from .api.routers.plus import router as plus_router
    from .api.routers.scan import router as scan_router
    from .api.routers.synastry import router as syn_router

    app.add_middleware(GZipMiddleware, minimum_size=512)
    install_error_handlers(app)

    app.include_router(plus_router)
    app.include_router(interpret_router)
    app.include_router(natals_router)
    app.include_router(analysis_router)
    app.include_router(scan_router, prefix="/v1/scan", tags=["scan"])
    app.include_router(syn_router, prefix="/v1/synastry", tags=["synastry"])

# >>> AUTO-GEN BEGIN: api-natals v1.0
if app:
    pass
# >>> AUTO-GEN END: api-natals v1.0
