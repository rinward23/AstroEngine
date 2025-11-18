"""Helpers for paginated AstroEngine endpoints."""
from __future__ import annotations

from typing import AsyncIterator, Iterator, Optional, Type, TypeVar

from pydantic import BaseModel

if False:  # pragma: no cover - for type checkers only
    from .client import AsyncClient, Client

T = TypeVar("T", bound=BaseModel)


def parse_page(items, model: Optional[Type[T]]) -> list[T] | list[dict]:
    if model is None:
        return items
    return [model.model_validate(item) for item in items]


def paginate(client: "Client", path: str, *, model: Optional[Type[T]] = None, params=None) -> Iterator[list[T] | list[dict]]:
    for page in client.paginate(path, params=params):
        yield parse_page(page, model)


async def paginate_async(
    client: "AsyncClient",
    path: str,
    *,
    model: Optional[Type[T]] = None,
    params=None,
) -> AsyncIterator[list[T] | list[dict]]:
    async for page in client.paginate(path, params=params):
        yield parse_page(page, model)
