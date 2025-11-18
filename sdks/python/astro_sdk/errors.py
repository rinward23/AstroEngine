"""Exception hierarchy for the AstroEngine SDK."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(slots=True)
class ApiError(Exception):
    """Base error containing standard AstroEngine fields."""

    code: str
    status_code: int
    message: str
    payload: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:  # pragma: no cover - convenience string repr
        return f"{self.status_code} {self.code}: {self.message}"


class RateLimitedError(ApiError):
    """Raised for HTTP 429 responses."""

    retry_after_ms: Optional[int] = None


class InvalidBodyError(ApiError):
    """Raised when the API rejects a payload."""


def is_rate_limited(error: BaseException) -> bool:
    return isinstance(error, RateLimitedError)


def is_invalid_body(error: BaseException) -> bool:
    return isinstance(error, InvalidBodyError)
