"""Uvicorn launcher that scales workers with detected CPU capacity."""

from __future__ import annotations

import os
from typing import Optional

import uvicorn


def _env_positive_int(name: str) -> Optional[int]:
    """Return a positive integer from ``name`` if it is well-formed."""

    raw = os.getenv(name)
    if raw is None:
        return None
    value = raw.strip()
    if not value or value.lower() == "auto":
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def determine_worker_count() -> int:
    """Compute the uvicorn worker count based on env overrides or CPU cores."""

    explicit = _env_positive_int("UVICORN_WORKERS")
    if explicit is not None:
        return explicit
    cpu_count = os.cpu_count() or 1
    return max(1, cpu_count)


def main() -> None:
    """Launch the FastAPI app with an adaptive worker count."""

    host = os.getenv("UVICORN_HOST", "0.0.0.0")
    port = int(os.getenv("UVICORN_PORT", os.getenv("PORT", "8000")))
    timeout_keep_alive = _env_positive_int("UVICORN_TIMEOUT_KEEP_ALIVE") or 10
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        workers=determine_worker_count(),
        timeout_keep_alive=timeout_keep_alive,
    )


__all__ = ["determine_worker_count", "main"]


if __name__ == "__main__":
    main()
