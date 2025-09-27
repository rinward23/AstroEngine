
"""Declarative base used by Alembic to reflect AstroEngine Plus models."""


from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):

    """Shared declarative base ensuring a single metadata tree for migrations."""

    pass


__all__ = ["Base"]

