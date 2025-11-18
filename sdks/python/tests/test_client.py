import asyncio

import httpx
import pytest

from astro_sdk.client import AsyncClient, Client


@pytest.fixture(autouse=True)
def _fast_sleep(monkeypatch):
    monkeypatch.setattr("astro_sdk.client.time.sleep", lambda _s: None)
    monkeypatch.setattr("astro_sdk.client.asyncio.sleep", lambda _s: asyncio.sleep(0))


def test_client_attaches_idempotency_headers():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = request.headers
        return httpx.Response(200, json={"data": []})

    transport = httpx.MockTransport(handler)
    client = Client(transport=transport)
    with client.idempotent("abc-123"):
        client.request("POST", "/charts", json_body={"label": "demo"})
    assert captured["headers"]["Idempotency-Key"] == "abc-123"


def test_client_retries_on_rate_limits():
    responses = [
        httpx.Response(429, json={"code": "rate_limited"}, headers={"Retry-After": "0"}),
        httpx.Response(200, json={"data": []}),
    ]

    def handler(_: httpx.Request) -> httpx.Response:
        return responses.pop(0)

    client = Client(transport=httpx.MockTransport(handler))
    data = client.request("GET", "/charts")
    assert data == {"data": []}


def test_async_client_streams_ndjson():
    content = "{\"id\":1}\n{\"id\":2}\n"

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=content.encode("utf-8"))

    client = AsyncClient(transport=httpx.MockTransport(handler))

    async def _collect():
        results = []
        async for chunk in client.stream("/charts"):
            results.append(chunk)
        await client.aclose()
        return results

    results = asyncio.run(_collect())
    assert results == [{"id": 1}, {"id": 2}]


def test_pagination_helper():
    responses = [
        httpx.Response(200, json={"data": [{"id": 1}], "next": "/charts?page=2"}),
        httpx.Response(200, json={"data": [{"id": 2}], "next": None}),
    ]

    def handler(_: httpx.Request) -> httpx.Response:
        return responses.pop(0)

    client = Client(transport=httpx.MockTransport(handler))
    aggregated = []
    for page in client.paginate("/charts"):
        aggregated.extend(page)
    assert aggregated == [{"id": 1}, {"id": 2}]
