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
    def _parse_csv(cls, value: str | Iterable[str] | None) -> tuple[str, ...]:
        if value is None:
            return tuple()
        if isinstance(value, str):
            items = (item.strip() for item in value.split(","))
        else:
            items = (str(item).strip() for item in value)
        normalized: list[str] = []
        seen: set[str] = set()
        normalised: list[str] = []
        for item in _iter_items(value):
            if item and item not in seen:
                normalised.append(item)
                seen.add(item)
        return tuple(normalized)

    @classmethod
    def from_env(cls) -> "ServiceSettings":
        """Construct settings using the process environment."""

        redis_url = os.getenv("RELATIONSHIP_REDIS_URL") or os.getenv("REDIS_URL")
        rate_limit = max(1, int(os.getenv("RELATIONSHIP_RATE_LIMIT", "60")))
        gzip_min_size = max(128, int(os.getenv("RELATIONSHIP_GZIP_MIN", "512")))
        request_max = max(32_768, int(os.getenv("RELATIONSHIP_REQUEST_MAX", "1000000")))
        enable_etag = os.getenv("RELATIONSHIP_DISABLE_ETAG") not in {"1", "true", "TRUE"}
        environment = os.getenv("ENV", "dev")
        settings = cls(
            cors_allow_origins=os.getenv("CORS_ALLOW_ORIGINS"),
            rate_limit_per_minute=max(1, rate_limit),
            redis_url=redis_url,
            gzip_minimum_size=gzip_min_size,
            request_max_bytes=request_max,
            enable_etag=enable_etag,
            environment=environment,
        )
        if settings.environment == "dev" and not settings.cors_allow_origins:
            settings = settings.model_copy(update={"cors_allow_origins": ("*",)})
        return settings

    def cors_origin_list(self) -> tuple[str, ...]:
        if self.cors_allow_origins:
            return self.cors_allow_origins
        if self.environment == "dev":
            return ("*",)
        return tuple()


__all__ = ["ServiceSettings"]
