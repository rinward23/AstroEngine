# >>> AUTO-GEN BEGIN: api-skeleton v1.0
from __future__ import annotations

try:
    from fastapi import FastAPI
    from pydantic import BaseModel
except Exception as e:  # pragma: no cover
    FastAPI = None  # type: ignore

app = FastAPI(title="AstroEngine API") if FastAPI else None

class Health(BaseModel):
    ok: bool

if app:
    @app.get("/health", response_model=Health)
    def health() -> Health:  # pragma: no cover - trivial
        return Health(ok=True)


def run() -> None:
    """Launch the API server if dependencies are installed."""
    if app is None:
        raise RuntimeError("API extra not installed. Use: pip install -e .[api]")
    import uvicorn  # type: ignore
    uvicorn.run(app, host="0.0.0.0", port=8099)
# >>> AUTO-GEN END: api-skeleton v1.0
