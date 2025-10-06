"""Pagination helpers used across AstroEngine API routers."""

from __future__ import annotations

from fastapi import Query
from pydantic import BaseModel, Field

MAX_PAGE_SIZE = 100


class Pagination(BaseModel):
    """Normalized pagination parameters."""

    page: int = Field(default=1, ge=1, description="1-indexed page number.")
    page_size: int = Field(
        default=25,
        ge=1,
        le=MAX_PAGE_SIZE,
        description="Number of items to return per page.",
    )

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


def get_pagination(
    page: int = Query(1, ge=1, description="1-indexed page number."),
    page_size: int = Query(
        25,
        ge=1,
        le=MAX_PAGE_SIZE,
        description="Number of items to include in the response page (max 100).",
    ),
) -> Pagination:
    """Dependency for list endpoints to inject pagination constraints."""

    return Pagination(page=page, page_size=page_size)


__all__ = ["MAX_PAGE_SIZE", "Pagination", "get_pagination"]

