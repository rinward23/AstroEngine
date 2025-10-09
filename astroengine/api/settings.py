"""Runtime configuration for the public API service."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable

__all__ = ["APISettings", "settings", "get_settings"]


def _parse_bool(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _parse_origins(value: str | Iterable[str] | None) -> tuple[str, ...]:
    if value is None:
        return tuple()
    if isinstance(value, str):
        raw_items = value.split(",")
    else:
        raw_items = list(value)
    seen: set[str] = set()
    origins: list[str] = []
    for item in raw_items:
        normalised = str(item).strip()
        if not normalised:
            continue
        if normalised in seen:
            continue
        origins.append(normalised)
        seen.add(normalised)
    return tuple(origins)


@dataclass(slots=True)
class APISettings:
    """Settings derived from the environment for API runtime concerns."""

    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    log_level: str = "info"
    cors_origins: tuple[str, ...] = tuple()

    @classmethod
    def from_env(cls) -> "APISettings":
        host = os.getenv("ASTROENGINE_API_HOST", os.getenv("UVICORN_HOST", "0.0.0.0"))
        port_raw = os.getenv("ASTROENGINE_API_PORT", os.getenv("UVICORN_PORT", "8000"))
        try:
            port = int(port_raw)
        except (TypeError, ValueError):  # pragma: no cover - defensive guard
            port = 8000

        reload_flag = _parse_bool(
            os.getenv("ASTROENGINE_API_RELOAD", os.getenv("UVICORN_RELOAD")),
            default=False,
        )
        log_level = os.getenv("ASTROENGINE_API_LOG_LEVEL", "info")

        raw_origins = os.getenv("ASTROENGINE_API_CORS_ORIGINS")
        if raw_origins is None:
            raw_origins = os.getenv("CORS_ALLOW_ORIGINS")

        cors_origins = _parse_origins(raw_origins)

        return cls(
            host=host,
            port=port,
            reload=reload_flag,
            log_level=log_level,
            cors_origins=cors_origins,
        )


@lru_cache(maxsize=1)
def get_settings() -> APISettings:
    """Return cached API settings derived from the environment."""

    return APISettings.from_env()


settings: APISettings = get_settings()

