"""Runtime configuration helpers for the relationship API."""

from __future__ import annotations

import os
from typing import Iterable, Iterator

from pydantic import BaseModel, Field, field_validator


def _iter_items(value: str | Iterable[str]) -> Iterator[str]:
    """Yield individual comma-separated items from user-provided origin values."""

    if isinstance(value, str):
        for chunk in value.split(","):
            yield chunk.strip()
    else:
        for item in value:
            yield str(item).strip()


class ServiceSettings(BaseModel):
    """Container for environment-derived settings."""

    cors_allow_origins: tuple[str, ...] = Field(default_factory=tuple)
    environment: str = "dev"
    rate_limit_per_minute: int = 60
    redis_url: str | None = None
    gzip_minimum_size: int = 512
    request_max_bytes: int = 1_000_000
    enable_etag: bool = True

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def _normalise_origins(cls, value: str | Iterable[str] | None) -> tuple[str, ...]:
        if value in (None, ""):
            return tuple()

        seen: set[str] = set()
        normalised: list[str] = []
        for item in _iter_items(value):
            if item and item not in seen:
                normalised.append(item)
                seen.add(item)
        return tuple(normalised)

    @classmethod
    def from_env(cls) -> "ServiceSettings":
        """Initialise settings from environment variables."""

        env_get = os.getenv
        cors_raw = env_get("RELATIONSHIP_CORS_ALLOW_ORIGINS")
        if cors_raw is None:
            cors_raw = env_get("CORS_ALLOW_ORIGINS")

        settings = cls(
            cors_allow_origins=cors_raw,
            environment=env_get("ENV", "dev"),
            rate_limit_per_minute=max(1, int(env_get("RELATIONSHIP_RATE_LIMIT", "60"))),
            redis_url=env_get("RELATIONSHIP_REDIS_URL") or env_get("REDIS_URL"),
            gzip_minimum_size=max(128, int(env_get("RELATIONSHIP_GZIP_MIN", "512"))),
            request_max_bytes=max(32_768, int(env_get("RELATIONSHIP_REQUEST_MAX", "1000000"))),
            enable_etag=env_get("RELATIONSHIP_DISABLE_ETAG") not in {"1", "true", "TRUE"},
        )

        if settings.environment == "dev" and not settings.cors_allow_origins:
            return settings.model_copy(update={"cors_allow_origins": ("*",)})
        return settings

    def cors_origin_list(self) -> tuple[str, ...]:
        if self.cors_allow_origins:
            return self.cors_allow_origins
        if self.environment == "dev":
            return ("*",)
        return tuple()


__all__ = ["ServiceSettings"]
