"""Runtime configuration helpers for the relationship API."""

from __future__ import annotations

import os
from typing import Iterable, Sequence

from pydantic import BaseModel, Field, field_validator


def _parse_origins(raw: str | Sequence[str] | None) -> tuple[str, ...]:
    """Normalize comma-separated CORS origin declarations."""

    if raw is None:
        return tuple()
    if isinstance(raw, str):
        candidates = (segment.strip() for segment in raw.split(","))
    else:
        candidates = (str(segment).strip() for segment in raw)
    normalized: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate and candidate not in seen:
            normalized.append(candidate)
            seen.add(candidate)
    return tuple(normalized)


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
    def _parse_csv(cls, value: str | Sequence[str] | None) -> tuple[str, ...]:
        return _parse_origins(value)

    @classmethod
    def from_env(cls) -> "ServiceSettings":
        """Construct settings using the process environment."""

        redis_url = os.getenv("RELATIONSHIP_REDIS_URL") or os.getenv("REDIS_URL")
        rate_limit = max(1, int(os.getenv("RELATIONSHIP_RATE_LIMIT", "60")))
        gzip_min_size = max(128, int(os.getenv("RELATIONSHIP_GZIP_MIN", "512")))
        request_max = max(32_768, int(os.getenv("RELATIONSHIP_REQUEST_MAX", "1000000")))
        enable_etag = os.getenv("RELATIONSHIP_DISABLE_ETAG") not in {"1", "true", "TRUE"}
        environment = os.getenv("ENV", "dev")
        cors_allow_origins = _parse_origins(os.getenv("CORS_ALLOW_ORIGINS"))

        settings = cls(
            cors_allow_origins=cors_allow_origins,
            rate_limit_per_minute=rate_limit,
            redis_url=redis_url,
            gzip_minimum_size=gzip_min_size,
            request_max_bytes=request_max,
            enable_etag=enable_etag,
            environment=environment,
        )
        if settings.environment == "dev" and not settings.cors_allow_origins:
            settings = settings.model_copy(update={"cors_allow_origins": ("*",)})
        return settings

    def cors_origin_list(self) -> Iterable[str]:
        if self.cors_allow_origins:
            return self.cors_allow_origins
        if self.environment == "dev":
            return ("*",)
        return tuple()


__all__ = ["ServiceSettings"]
