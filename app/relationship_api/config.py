"""Runtime configuration helpers for the relationship API."""

from __future__ import annotations

import os
from collections.abc import Iterable, Iterator

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
    cors_allow_methods: tuple[str, ...] = Field(default=("GET", "POST", "OPTIONS"))
    cors_allow_headers: tuple[str, ...] = Field(
        default=("Authorization", "Content-Type", "If-None-Match", "X-Requested-With")
    )
    environment: str = "dev"
    rate_limit_per_minute: int = 60
    redis_url: str | None = None
    gzip_minimum_size: int = 512
    request_max_bytes: int = 1_000_000
    enable_etag: bool = True
    tls_terminates_upstream: bool = False
    enable_hsts: bool = False
    hsts_max_age: int = 31536000

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def _parse_csv(cls, value: str | Iterable[str] | None) -> tuple[str, ...]:
        if value is None:
            return tuple()
        seen: set[str] = set()
        normalised: list[str] = []
        for item in _iter_items(value):
            if item and item not in seen:
                normalised.append(item)
                seen.add(item)
        return tuple(normalised)

    @field_validator("cors_allow_methods", mode="before")
    @classmethod
    def _parse_methods(
        cls, value: str | Iterable[str] | None
    ) -> tuple[str, ...]:
        if value is None:
            return ("GET", "POST", "OPTIONS")
        return tuple(item.upper() for item in _iter_items(value) if item)

    @field_validator("cors_allow_headers", mode="before")
    @classmethod
    def _parse_headers(
        cls, value: str | Iterable[str] | None
    ) -> tuple[str, ...]:
        if value is None:
            return ("Authorization", "Content-Type", "If-None-Match", "X-Requested-With")
        seen: set[str] = set()
        headers: list[str] = []
        for item in _iter_items(value):
            normalised = item
            if normalised and normalised.lower() not in seen:
                headers.append(normalised)
                seen.add(normalised.lower())
        return tuple(headers)

    @staticmethod
    def _parse_bool(value: str | None, default: bool = False) -> bool:
        if value is None:
            return default
        return value.lower() in {"1", "true", "yes", "on"}

    @classmethod
    def from_env(cls) -> ServiceSettings:
        """Construct settings using the process environment."""

        redis_url = os.getenv("RELATIONSHIP_REDIS_URL") or os.getenv("REDIS_URL")
        rate_limit = max(1, int(os.getenv("RELATIONSHIP_RATE_LIMIT", "60")))
        gzip_min_size = max(128, int(os.getenv("RELATIONSHIP_GZIP_MIN", "512")))
        request_max = max(32_768, int(os.getenv("RELATIONSHIP_REQUEST_MAX", "1000000")))
        enable_etag = os.getenv("RELATIONSHIP_DISABLE_ETAG") not in {"1", "true", "TRUE"}
        environment = os.getenv("ENV", "dev")
        tls_upstream = cls._parse_bool(os.getenv("RELATIONSHIP_TLS_UPSTREAM"))
        enable_hsts = cls._parse_bool(os.getenv("RELATIONSHIP_ENABLE_HSTS"), default=tls_upstream)
        hsts_max_age = max(0, int(os.getenv("RELATIONSHIP_HSTS_MAX_AGE", "31536000")))
        settings = cls(
            cors_allow_origins=os.getenv("CORS_ALLOW_ORIGINS"),
            cors_allow_methods=os.getenv("CORS_ALLOW_METHODS"),
            cors_allow_headers=os.getenv("CORS_ALLOW_HEADERS"),
            rate_limit_per_minute=max(1, rate_limit),
            redis_url=redis_url,
            gzip_minimum_size=gzip_min_size,
            request_max_bytes=request_max,
            enable_etag=enable_etag,
            environment=environment,
            tls_terminates_upstream=tls_upstream,
            enable_hsts=enable_hsts,
            hsts_max_age=hsts_max_age,
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
