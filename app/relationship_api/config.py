"""Runtime configuration helpers for the relationship API."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from typing import Iterable


@dataclass(slots=True)
class ServiceSettings:
    """Container for environment-derived settings."""

    cors_allow_origins: tuple[str, ...] = field(default_factory=tuple)
    rate_limit_per_minute: int = 60
    redis_url: str | None = None
    gzip_minimum_size: int = 512
    request_max_bytes: int = 1_000_000
    enable_etag: bool = True

    @classmethod
    def from_env(cls) -> "ServiceSettings":
        def _parse_origins(value: str | None) -> tuple[str, ...]:
            if not value:
                return tuple()
            parts = [item.strip() for item in value.split(",")]
            return tuple(sorted({p for p in parts if p}))

        redis_url = os.getenv("RELATIONSHIP_REDIS_URL") or os.getenv("REDIS_URL")
        rate_limit = int(os.getenv("RELATIONSHIP_RATE_LIMIT", "60"))
        gzip_min_size = int(os.getenv("RELATIONSHIP_GZIP_MIN", "512"))
        request_max = int(os.getenv("RELATIONSHIP_REQUEST_MAX", "1000000"))
        enable_etag = os.getenv("RELATIONSHIP_DISABLE_ETAG") not in {"1", "true", "TRUE"}
        return cls(
            cors_allow_origins=_parse_origins(os.getenv("CORS_ALLOW_ORIGINS")),
            rate_limit_per_minute=max(1, rate_limit),
            redis_url=redis_url,
            gzip_minimum_size=max(128, gzip_min_size),
            request_max_bytes=max(32_768, request_max),
            enable_etag=enable_etag,
        )

    def cors_origin_list(self) -> Iterable[str]:
        if self.cors_allow_origins:
            return self.cors_allow_origins
        return ("*",)


__all__ = ["ServiceSettings"]
