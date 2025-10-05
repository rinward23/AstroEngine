"""Shared response helpers for FastAPI endpoints."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Iterator
from typing import Any, Mapping

from fastapi.responses import Response, StreamingResponse

from astroengine.utils import json as json_utils


def _json_bytes(value: Any, *, sort_keys: bool = False) -> bytes:
    """Serialize *value* using :mod:`orjson` if available."""

    option = json_utils.OPT_SORT_KEYS if sort_keys else None
    return json_utils.dumps(value, option=option)


def json_response(
    value: Any,
    *,
    status_code: int = 200,
    headers: Mapping[str, str] | None = None,
    sort_keys: bool = False,
) -> Response:
    """Return a JSON :class:`~fastapi.responses.Response` encoded with ``orjson``."""

    payload = _json_bytes(value, sort_keys=sort_keys)
    return Response(
        content=payload,
        status_code=status_code,
        media_type="application/json",
        headers=dict(headers or {}),
    )


def _strip_etag(value: str) -> str:
    if value.startswith("W/"):
        value = value[2:]
    if value.startswith('"') and value.endswith('"') and len(value) >= 2:
        return value[1:-1]
    return value


def _parse_if_none_match(raw: str | None) -> set[str]:
    if not raw:
        return set()
    candidates = {token.strip() for token in raw.split(",") if token.strip()}
    parsed = {"*" if token == "*" else _strip_etag(token) for token in candidates}
    return parsed


def _etag_for(payload: bytes) -> str:
    digest = hashlib.blake2b(payload, digest_size=16).hexdigest()
    return f'"{digest}"'


def conditional_json_response(
    value: Any,
    *,
    if_none_match: str | None,
    status_code: int = 200,
    max_age: int = 3600,
    headers: Mapping[str, str] | None = None,
    sort_keys: bool = True,
) -> Response:
    """Return a cached JSON response honouring ``If-None-Match`` semantics."""

    payload = _json_bytes(value, sort_keys=sort_keys)
    etag = _etag_for(payload)
    etag_token = _strip_etag(etag)
    requested = _parse_if_none_match(if_none_match)
    cache_headers = {
        "ETag": etag,
        "Cache-Control": f"public, max-age={max_age}, immutable",
    }
    if headers:
        cache_headers.update(headers)
    if "*" in requested or etag_token in requested:
        return Response(status_code=304, headers=cache_headers)
    return Response(
        content=payload,
        status_code=status_code,
        media_type="application/json",
        headers=cache_headers,
    )


def etag_matches(etag: str, candidates: str | None) -> bool:
    """Return ``True`` if *etag* appears in the supplied header value."""

    requested = _parse_if_none_match(candidates)
    return bool(requested) and ("*" in requested or _strip_etag(etag) in requested)


def _ndjson_iterator(items: Iterable[Any]) -> Iterator[bytes]:
    for item in items:
        yield _json_bytes(item) + b"\n"


def ndjson_stream(items: Iterable[Any], *, media_type: str = "application/x-ndjson") -> StreamingResponse:
    """Return a streaming NDJSON response for *items*."""

    return StreamingResponse(_ndjson_iterator(items), media_type=media_type)


__all__ = [
    "conditional_json_response",
    "etag_matches",
    "json_response",
    "ndjson_stream",
]

