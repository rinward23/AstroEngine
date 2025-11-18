"""Webhook helpers shared by the CLI and SDK implementations."""

from __future__ import annotations

import hmac
import json
import time
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

__all__ = [
    "DEFAULT_TOLERANCE_SECONDS",
    "WebhookSignatureError",
    "SignatureExpiredError",
    "InvalidSignatureError",
    "parse_signature_header",
    "compute_signature",
    "verify_signature",
]

DEFAULT_TOLERANCE_SECONDS = 300


class WebhookSignatureError(RuntimeError):
    """Base exception for webhook verification failures."""


class SignatureExpiredError(WebhookSignatureError):
    """Raised when the signature timestamp drifts beyond the allowed tolerance."""


class InvalidSignatureError(WebhookSignatureError):
    """Raised when the supplied signature does not match the computed digest."""


def _coerce_payload_bytes(payload: Any) -> bytes:
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, str):
        return payload.encode("utf-8")
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _coerce_secret_bytes(secret: str | bytes) -> bytes:
    return secret.encode("utf-8") if isinstance(secret, str) else secret


@dataclass(frozen=True, slots=True)
class ParsedSignature:
    """Parsed representation of the ``X-Astro-Signature`` header."""

    timestamp: int
    digest: str


def parse_signature_header(header: str) -> ParsedSignature:
    """Parse ``X-Astro-Signature`` header contents into a structured object."""

    if not header:
        raise InvalidSignatureError("signature header is required")
    timestamp_value: int | None = None
    digest_value: str | None = None
    for part in header.split(","):
        key, _, raw_value = part.strip().partition("=")
        if not _:
            continue
        key = key.strip().lower()
        value = raw_value.strip()
        if key == "t":
            try:
                timestamp_value = int(value)
            except ValueError as exc:  # pragma: no cover - defensive guard
                raise InvalidSignatureError("invalid timestamp in signature header") from exc
        elif key == "v1":
            digest_value = value
    if timestamp_value is None or digest_value is None:
        raise InvalidSignatureError("signature header missing timestamp or digest")
    return ParsedSignature(timestamp_value, digest_value)


def compute_signature(secret: str | bytes, timestamp: int | str, payload: Any) -> str:
    """Compute the expected v1 signature for ``payload`` at ``timestamp``."""

    secret_bytes = _coerce_secret_bytes(secret)
    message = f"{timestamp}".encode("ascii") + b"." + _coerce_payload_bytes(payload)
    return hmac.new(secret_bytes, message, sha256).hexdigest()


def verify_signature(
    payload: Any,
    header: str,
    secret: str | bytes,
    *,
    tolerance_seconds: int = DEFAULT_TOLERANCE_SECONDS,
    now: int | float | None = None,
) -> ParsedSignature:
    """Validate ``payload`` against ``header`` using ``secret``.

    Parameters
    ----------
    payload:
        Request body forwarded by the webhook.
    header:
        Raw ``X-Astro-Signature`` header value (``t=<unix>, v1=<hex>``).
    secret:
        Shared secret provisioned for the webhook endpoint.
    tolerance_seconds:
        Maximum clock skew tolerated before rejecting the signature.
    now:
        Override the current timestamp for deterministic testing.
    """

    parsed = parse_signature_header(header)
    current_time = int(now if now is not None else time.time())
    if tolerance_seconds > 0 and abs(current_time - parsed.timestamp) > tolerance_seconds:
        raise SignatureExpiredError(
            f"signature timestamp {parsed.timestamp} is older than {tolerance_seconds}s"
        )
    expected = compute_signature(secret, parsed.timestamp, payload)
    if not hmac.compare_digest(expected, parsed.digest):
        raise InvalidSignatureError("signature digest does not match payload")
    return ParsedSignature(parsed.timestamp, expected)
