"""Runtime configuration helpers for the relationship API."""

from __future__ import annotations

import os
from typing import Iterable

from pydantic import BaseModel, Field, field_validator


class ServiceSettings(BaseModel):
    """Container for environment-derived settings."""

    cors_allow_origins: list[str] = Field(
        default_factory=list,
        description="Comma-separated list of allowed CORS origins (empty by default).",
    )
    rate_limit_per_minute: int = 60
    redis_url: str | None = None
    gzip_minimum_size: int = 512
    request_max_bytes: int = 1_000_000
    enable_etag: bool = True

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def _parse_csv(cls, value: str | Iterable[str] | None):
        if value is None:
            return []
        if isinstance(value, str):
            items = (item.strip() for item in value.split(","))
        else:
            items = (str(item).strip() for item in value)
        normalized: list[str] = []
        seen: set[str] = set()
        for item in items:
            if item and item not in seen:
                normalized.append(item)
                seen.add(item)
        return normalized

    @classmethod
    def from_env(cls) -> "ServiceSettings":
        redis_url = os.getenv("RELATIONSHIP_REDIS_URL") or os.getenv("REDIS_URL")
        rate_limit = int(os.getenv("RELATIONSHIP_RATE_LIMIT", "60"))
        gzip_min_size = int(os.getenv("RELATIONSHIP_GZIP_MIN", "512"))
        request_max = int(os.getenv("RELATIONSHIP_REQUEST_MAX", "1000000"))
        enable_etag = os.getenv("RELATIONSHIP_DISABLE_ETAG") not in {"1", "true", "TRUE"}
        env_name = (
            os.getenv("ENV")
            or os.getenv("ASTROENGINE_ENV")
            or "production"
        ).strip().lower()
        settings = cls(
            cors_allow_origins=os.getenv("CORS_ALLOW_ORIGINS"),
            rate_limit_per_minute=max(1, rate_limit),
            redis_url=redis_url,
            gzip_minimum_size=max(128, gzip_min_size),
            request_max_bytes=max(32_768, request_max),
            enable_etag=enable_etag,
        )
        if env_name in {"dev", "development"} and not settings.cors_allow_origins:
            settings.cors_allow_origins = ["*"]
        return settings

    def cors_origin_list(self) -> Iterable[str]:
        return tuple(self.cors_allow_origins)


__all__ = ["ServiceSettings"]
