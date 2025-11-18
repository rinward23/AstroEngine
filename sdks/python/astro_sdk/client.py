"""HTTP clients for the AstroEngine API."""
from __future__ import annotations

import asyncio
import json
import time
from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncGenerator, Dict, Generator, Optional

import httpx

from .errors import ApiError, InvalidBodyError, RateLimitedError
from .generated.schema import RELEASE_METADATA

DEFAULT_BASE_URL = "https://api.astroengine.local"
DEFAULT_TIMEOUT = 30.0


def _user_agent(suffix: Optional[str] = None) -> str:
    dataset_suffix = (
        f"(+solarfire-hash:{RELEASE_METADATA['datasets']['solarfire']};"
        f"swiss:{RELEASE_METADATA['datasets']['swiss_ephemeris']};"
        f"schema:{RELEASE_METADATA['schema_version']})"
    )
    values = ["AstroEnginePy/0.1.0", dataset_suffix, suffix]
    return " ".join(filter(None, values))


def _prepare_headers(token: Optional[str], suffix: Optional[str]) -> Dict[str, str]:
    headers = {
        "User-Agent": _user_agent(suffix),
        "AstroEngine-Schema": RELEASE_METADATA["schema_version"],
        "Content-Type": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _error_from_response(response: httpx.Response) -> ApiError:
    try:
        payload = response.json()
    except json.JSONDecodeError:
        payload = {}

    code = payload.get("code", f"HTTP_{response.status_code}")
    message = payload.get("message", response.reason_phrase)

    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After")
        error = RateLimitedError(code=code, status_code=response.status_code, message=message, payload=payload)
        if retry_after and retry_after.isdigit():
            error.retry_after_ms = int(retry_after) * 1000
        return error

    if response.status_code == 400:
        return InvalidBodyError(code=code, status_code=response.status_code, message=message, payload=payload)

    return ApiError(code=code, status_code=response.status_code, message=message, payload=payload)


class _Retry:
    def __init__(self, max_attempts: int = 5, base_delay: float = 0.2, max_delay: float = 5.0) -> None:
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay

    def _next_delay(self, attempt: int, retry_after_ms: Optional[int]) -> float:
        if retry_after_ms:
            return retry_after_ms / 1000
        delay = min(self.base_delay * (2 ** max(attempt - 1, 0)), self.max_delay)
        return delay

    def run(self, func):
        attempt = 0
        while True:
            try:
                return func()
            except RateLimitedError as exc:
                attempt += 1
                if attempt >= self.max_attempts:
                    raise
                time.sleep(self._next_delay(attempt, exc.retry_after_ms))

    async def run_async(self, func):
        attempt = 0
        while True:
            try:
                return await func()
            except RateLimitedError as exc:
                attempt += 1
                if attempt >= self.max_attempts:
                    raise
                await asyncio.sleep(self._next_delay(attempt, exc.retry_after_ms))


class Client:
    """Synchronous HTTP client with retry, pagination, and streaming helpers."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        token: Optional[str] = None,
        user_agent_suffix: Optional[str] = None,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self._headers = _prepare_headers(token, user_agent_suffix)
        self._client = httpx.Client(base_url=base_url, timeout=timeout, headers=self._headers, transport=transport)
        self._retry = _Retry()
        self._idempotency_key: Optional[str] = None

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, *exc_info) -> None:  # type: ignore[override]
        self.close()

    @contextmanager
    def idempotent(self, key: str) -> Generator["Client", None, None]:
        previous = self._idempotency_key
        self._idempotency_key = key
        try:
            yield self
        finally:
            self._idempotency_key = previous

    def _request(self, method: str, path: str, *, params: Optional[Dict[str, Any]] = None, json_body: Optional[Dict[str, Any]] = None) -> Any:
        def call() -> Any:
            headers = dict(self._headers)
            if self._idempotency_key:
                headers["Idempotency-Key"] = self._idempotency_key
            response = self._client.request(method, path, params=params, json=json_body, headers=headers)
            if 200 <= response.status_code < 300:
                if response.status_code == 204:
                    return None
                return response.json()
            raise _error_from_response(response)

        return self._retry.run(call)

    def request(self, method: str, path: str, *, params: Optional[Dict[str, Any]] = None, json_body: Optional[Dict[str, Any]] = None) -> Any:
        return self._request(method, path, params=params, json_body=json_body)

    def paginate(self, path: str, *, params: Optional[Dict[str, Any]] = None) -> Generator[list[Dict[str, Any]], None, None]:
        next_path: Optional[str] = path
        current_params = params or {}
        while next_path:
            payload = self.request("GET", next_path, params=current_params)
            data = payload.get("data", [])
            yield data
            next_path = payload.get("next")
            current_params = {}

    def stream(self, path: str, *, params: Optional[Dict[str, Any]] = None) -> Generator[Dict[str, Any], None, None]:
        with self._client.stream("GET", path, params=params, headers=self._headers) as response:
            if response.status_code >= 400:
                raise _error_from_response(response)
            for line in response.iter_lines():
                if not line:
                    continue
                yield json.loads(line)


class AsyncClient:
    """Async variant mirroring the synchronous `Client`."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        token: Optional[str] = None,
        user_agent_suffix: Optional[str] = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        self._headers = _prepare_headers(token, user_agent_suffix)
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            headers=self._headers,
            transport=transport,
        )
        self._retry = _Retry()
        self._idempotency_key: Optional[str] = None

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncClient":
        return self

    async def __aexit__(self, *exc_info) -> None:  # type: ignore[override]
        await self.aclose()

    @asynccontextmanager
    async def idempotent(self, key: str) -> AsyncGenerator["AsyncClient", None]:
        previous = self._idempotency_key
        self._idempotency_key = key
        try:
            yield self
        finally:
            self._idempotency_key = previous

    async def _request(self, method: str, path: str, *, params: Optional[Dict[str, Any]] = None, json_body: Optional[Dict[str, Any]] = None) -> Any:
        async def call() -> Any:
            headers = dict(self._headers)
            if self._idempotency_key:
                headers["Idempotency-Key"] = self._idempotency_key
            response = await self._client.request(method, path, params=params, json=json_body, headers=headers)
            if 200 <= response.status_code < 300:
                if response.status_code == 204:
                    return None
                return response.json()
            raise _error_from_response(response)

        return await self._retry.run_async(call)

    async def request(self, method: str, path: str, *, params: Optional[Dict[str, Any]] = None, json_body: Optional[Dict[str, Any]] = None) -> Any:
        return await self._request(method, path, params=params, json_body=json_body)

    async def paginate(self, path: str, *, params: Optional[Dict[str, Any]] = None) -> AsyncGenerator[list[Dict[str, Any]], None]:
        next_path: Optional[str] = path
        current_params = params or {}
        while next_path:
            payload = await self.request("GET", next_path, params=current_params)
            data = payload.get("data", [])
            yield data
            next_path = payload.get("next")
            current_params = {}

    async def stream(self, path: str, *, params: Optional[Dict[str, Any]] = None) -> AsyncGenerator[Dict[str, Any], None]:
        async with self._client.stream("GET", path, params=params, headers=self._headers) as response:
            if response.status_code >= 400:
                raise _error_from_response(response)
            async for line in response.aiter_lines():
                if not line:
                    continue
                yield json.loads(line)
